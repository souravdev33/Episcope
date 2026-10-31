"""Local Spark medallion pipeline with quarantine, de-identification and lineage."""
import argparse, hashlib, json, os, shutil
from datetime import datetime, timezone
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',default='data/input'); ap.add_argument('--output',default='data/lake'); ap.add_argument('--reference',default='data/reference'); a=ap.parse_args()
    from pyspark.sql import SparkSession, functions as F, types as T
    spark=(SparkSession.builder.appName('EpiScope').master('local[*]').config('spark.sql.shuffle.partitions','8').config('spark.sql.adaptive.enabled','true').getOrCreate())
    src=Path(a.input); out=Path(a.output); loaded=datetime.now(timezone.utc).isoformat()
    facility=spark.read.option('header',True).option('inferSchema',True).csv(str(src/'facilities.csv'))
    files=list(src.glob('encounters-*.csv'))+list((src/'incremental').glob('*.csv') if (src/'incremental').exists() else [])
    if not files: raise SystemExit(f'No encounter CSV found in {src}')
    def file_hash(path):
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
        return h.hexdigest()
    checksums={str(p.resolve()):file_hash(p) for p in files}
    batch=hashlib.sha256(json.dumps(checksums,sort_keys=True).encode()).hexdigest()[:20]
    df=spark.read.option('header',True).option('inferSchema',True).csv([str(p) for p in files])
    checksum_expr=F.lit(None).cast('string')
    for path,checksum in checksums.items():
        checksum_expr=F.when(F.input_file_name().endswith(Path(path).name),F.lit(checksum)).otherwise(checksum_expr)
    df=(df.withColumn('_source_file',F.input_file_name()).withColumn('file_checksum',checksum_expr).withColumn('batch_id',F.lit(batch)).withColumn('loaded_at',F.lit(loaded)))
    bronze=out/'bronze'/'encounters'; batch_dir=bronze/f'batch_id={batch}'
    if not batch_dir.exists(): df.write.mode('append').partitionBy('batch_id').parquet(str(bronze))
    # Keep latest observed row per encounter ID for idempotent replays.
    salt=os.environ.get('EPISCOPE_HASH_SALT')
    if not salt: raise SystemExit('Set EPISCOPE_HASH_SALT (see .env.example); secret must stay outside repository.')
    valid_icd=F.col('icd10_code').rlike(r'^(A90|A91|A00|A09|J10|J11|B5[0-4]|Z00)$')
    has_fac=facility.select('facility_id').dropDuplicates()
    valid_districts=[r.district for r in facility.select('district').distinct().collect()]
    from pyspark.sql import Window
    joined=(df.join(F.broadcast(has_fac.withColumn('_facility_ok',F.lit(True))), 'facility_id','left')
        .withColumn('_duplicate_count',F.count('*').over(Window.partitionBy('encounter_id'))))
    checks=[
      ('null_encounter',F.col('encounter_id').isNull()),('null_patient',F.col('patient_id').isNull()),
      ('null_facility',F.col('facility_id').isNull()),('null_district',F.col('district').isNull()),
      ('invalid_age',(~F.col('age_years').between(0,120))|F.col('age_years').isNull()),
      ('invalid_sex',~F.col('sex').isin('F','M','X')),('invalid_icd',~valid_icd),
      ('orphan_facility',F.col('_facility_ok').isNull()),('onset_after_report',F.to_date('onset_date')>F.to_date('report_date')),
      ('missing_onset',F.to_date('onset_date').isNull()),('missing_report',F.to_date('report_date').isNull()),
      ('invalid_geography',~F.col('district').isin(valid_districts)),('invalid_lab_flag',~F.col('lab_confirmed').isin(0,1)),
      ('invalid_admission_flag',~F.col('admitted').isin(0,1)),('duplicate_encounter',F.col('_duplicate_count')>1)]
    reason=F.concat_ws('|',*[F.when(test,F.lit(name)) for name,test in checks])
    tagged=joined.withColumn('quarantine_reason',reason)
    quarantine=tagged.filter(F.length('quarantine_reason')>0)
    quarantine.write.mode('overwrite').parquet(str(out/'silver'/'quarantine'))
    clean=(tagged.filter(F.length('quarantine_reason')==0)
      .withColumn('patient_hash',F.sha2(F.concat(F.lit(salt),F.col('patient_id')),256))
      .withColumn('onset_date',F.to_date('onset_date')).withColumn('report_date',F.to_date('report_date'))
      .withColumn('age_band',F.when(F.col('age_years')<5,'0-4').when(F.col('age_years')<18,'5-17').when(F.col('age_years')<50,'18-49').when(F.col('age_years')<65,'50-64').otherwise('65+'))
      .withColumn('disease',F.when(F.col('icd10_code').isin('A90','A91'),'dengue').when(F.col('icd10_code').isin('A00','A09'),'diarrhoea').when(F.col('icd10_code').isin('J10','J11'),'influenza').when(F.col('icd10_code').between('B50','B54'),'malaria').otherwise('other'))
      .withColumn('epi_year',F.year(F.expr('date_add(onset_date, CASE WHEN dayofweek(onset_date) = 1 THEN -3 ELSE 5 - dayofweek(onset_date) END)'))).withColumn('epi_week',F.weekofyear('onset_date'))
      .drop('patient_id','age_years','_facility_ok','_duplicate_count','quarantine_reason')
      .dropDuplicates(['encounter_id']))
    silver=out/'silver'/'encounters'
    clean.write.mode('overwrite').partitionBy('epi_year','epi_week').parquet(str(silver))
    gold=(clean.filter(F.col('disease')!='other').groupBy('district','disease','epi_year','epi_week')
      .agg(F.count('*').alias('cases'),F.sum('admitted').alias('admissions'),F.sum('lab_confirmed').alias('lab_confirmed'),
           F.max('loaded_at').alias('freshness'),F.collect_set('batch_id').alias('source_batch_ids')))
    reference=Path(a.reference)
    if (reference/'weather.csv').exists():
        weather=(spark.read.option('header',True).option('inferSchema',True).csv(str(reference/'weather.csv'))
          .withColumn('date',F.to_date('date')).withColumn('epi_year',F.year(F.expr('date_add(date, CASE WHEN dayofweek(date) = 1 THEN -3 ELSE 5 - dayofweek(date) END)')))
          .withColumn('epi_week',F.weekofyear('date')))
        weekly_weather=(weather.groupBy('district','epi_year','epi_week')
          .agg(F.sum('precipitation_mm').alias('precipitation_mm'),
               F.avg('temperature_c').alias('temperature_c'),
               F.avg('relative_humidity_pct').alias('relative_humidity_pct')))
        gold=gold.join(weekly_weather,['district','epi_year','epi_week'],'left')
    gold.write.mode('overwrite').partitionBy('epi_year','epi_week').parquet(str(out/'gold'/'weekly'))
    quality={'batch_id':batch,'loaded_at':loaded,'rows_in':df.count(),'rows_clean':clean.count(),'rows_quarantined':quarantine.count(),
             'rule_count':len(checks),'rules':{name:tagged.filter(test).count() for name,test in checks}}
    (out/'gold').mkdir(parents=True,exist_ok=True); (out/'gold'/'quality_report.json').write_text(json.dumps(quality,indent=2),encoding='utf-8')
    if (reference/'boundaries.geojson').exists():
        refout=out/'reference'; refout.mkdir(parents=True,exist_ok=True)
        shutil.copy2(reference/'boundaries.geojson',refout/'boundaries.geojson')
    if (reference/'source_metadata.json').exists():
        refout=out/'reference'; refout.mkdir(parents=True,exist_ok=True)
        shutil.copy2(reference/'source_metadata.json',refout/'source_metadata.json')
    # Silver/gold records retain bronze batch lineage via source_batch_ids in gold.
    spark.stop(); print(json.dumps(quality,indent=2))
if __name__=='__main__': main()



