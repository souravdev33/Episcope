"""Generate reproducible synthetic S4–S6 data. All generated records are fictional."""
import argparse, csv, json, random, re
from datetime import date, timedelta
from pathlib import Path

DISTRICTS = "Bagerhat,Bandarban,Barguna,Barishal,Bhola,Bogura,Brahmanbaria,Chandpur,Chapainawabganj,Chattogram,Chuadanga,Cox's Bazar,Cumilla,Dhaka,Dinajpur,Faridpur,Feni,Gaibandha,Gazipur,Gopalganj,Habiganj,Joypurhat,Jamalpur,Jashore,Jhalokati,Jhenaidah,Khagrachhari,Khulna,Kishoreganj,Kurigram,Kushtia,Lakshmipur,Lalmonirhat,Madaripur,Magura,Manikganj,Meherpur,Moulvibazar,Munshiganj,Mymensingh,Naogaon,Narail,Narayanganj,Narsingdi,Natore,Netrokona,Nilphamari,Noakhali,Pabna,Panchagarh,Patuakhali,Pirojpur,Rajbari,Rajshahi,Rangamati,Rangpur,Satkhira,Shariatpur,Sherpur,Sirajganj,Sunamganj,Sylhet,Tangail,Thakurgaon".split(",")
DISEASES = {"A90":"dengue","A00":"diarrhoea","J10":"influenza","B50":"malaria"}
START = date(2021,1,1)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--scale',type=float,default=.04); ap.add_argument('--seed',type=int,default=4345); ap.add_argument('--out',default='data/input'); ap.add_argument('--chunk',type=int,default=250000); ap.add_argument('--population-file'); a=ap.parse_args()
    if a.scale<=0: ap.error('--scale must be positive')
    rng=random.Random(a.seed); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    # Remove only this generator's previous numbered chunks so changing SF cannot
    # leave stale rows that get read by the downstream pipeline.
    for existing in out.glob('encounters-*.csv'):
        if re.fullmatch(r'encounters-\d{5,}\.csv', existing.name):
            existing.unlink()
    facilities=[]
    for i in range(640):
        d=DISTRICTS[i%64]; facilities.append({'facility_id':f'F{i:04d}','district':d,'facility_type':['hospital','upazila_health_complex','clinic'][i%3], 'beds':int(rng.triangular(8,500,55)), 'icu_beds':int(rng.triangular(0,60,4))})
    with (out/'facilities.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=facilities[0].keys()); w.writeheader(); w.writerows(facilities)
    population_path=out/'population.csv'
    if a.population_file:
        population_path.write_text(Path(a.population_file).read_text(encoding='utf-8'),encoding='utf-8')
    else:
        population_rows=[]
        for d in DISTRICTS:
            total=int(rng.uniform(700000,6000000)); male=round(total*.51); female=total-male
            shares=[.09,.27,.47,.10,.07]
            age_counts=[round(total*s) for s in shares]
            population_rows.append({'district':d,'population':total,'male_population':male,'female_population':female,
                'age_0_4':age_counts[0],'age_5_17':age_counts[1],'age_18_49':age_counts[2],
                'age_50_64':age_counts[3],'age_65_plus':age_counts[4]})
        with population_path.open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=population_rows[0].keys()); writer.writeheader(); writer.writerows(population_rows)
    with population_path.open(encoding='utf-8',newline='') as f:
        population_by_d={r['district']:{k:(float(v) if k!='district' else v) for k,v in r.items()} for r in csv.DictReader(f)}
    missing=set(DISTRICTS)-set(population_by_d)
    if missing: raise ValueError(f'Population file missing districts: {sorted(missing)}')
    district_weights=[population_by_d[d]['population'] for d in DISTRICTS]
    # Deterministic injected events are kept separate; analytics must not load this file.
    events=[]
    for n in range(30):
        events.append({'event_id':f'OUT{n+1:02d}','district':DISTRICTS[(n*7)%64], 'disease':list(DISEASES.values())[n%4], 'start_date':str(date(2021,1,1)+timedelta(days=40+n*52)), 'duration_days':int(rng.randint(14,56)), 'multiplier':round(rng.uniform(1.5,4.0),2)})
    events.append({'event_id':'OUT_NATIONWIDE','district':'ALL','disease':'novel_respiratory','start_date':'2024-02-01','duration_days':110,'multiplier':2.5})
    (out/'ground_truth_outbreaks.json').write_text(json.dumps(events,indent=2),encoding='utf-8')
    event_by_d={d:[] for d in DISTRICTS}; nationwide=[]
    for event in events:
        interval=(date.fromisoformat(event['start_date']),date.fromisoformat(event['start_date'])+timedelta(days=event['duration_days']),event['disease'],event['multiplier'])
        if event['district']=='ALL': nationwide.append(interval)
        else: event_by_d[event['district']].append(interval)
    hill={'Bandarban','Rangamati','Khagrachhari',"Cox's Bazar",'Chattogram'}
    target=max(1,int(25_000_000*a.scale)); facilities_by_d={d:[x['facility_id'] for x in facilities if x['district']==d] for d in DISTRICTS}
    codes=list(DISEASES); file_n=0; count=0
    while count<target:
        path=out/f'encounters-{file_n:05d}.csv'; file_n+=1
        with path.open('w',newline='',encoding='utf-8') as f:
            fields=['encounter_id','patient_id','facility_id','district','onset_date','report_date','age_years','sex','icd10_code','lab_confirmed','admitted','outcome']
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
            for _ in range(min(a.chunk,target-count)):
                d=(DISTRICTS[count] if count<len(DISTRICTS) else rng.choices(DISTRICTS,weights=district_weights,k=1)[0]); onset=START+timedelta(days=rng.randrange(1826)); delay=min(21,int(rng.expovariate(.32)))
                eid=f'E{count:09d}'; ifdup=count>0 and rng.random()<.02
                if ifdup: eid=f'E{max(0,count-rng.randrange(1,min(count,40)+1)):09d}'
                # Disease-specific seasonal and geographic risk; synthetic signal, not a fitted model.
                weights={
                    'A90':(3.0 if onset.month in (6,7,8,9,10) else .7)*(1.8 if d in ('Dhaka','Chattogram','Gazipur','Narayanganj') else 1),
                    'A00':(2.8 if onset.month in (3,4,5,6) else .8),
                    'J10':(2.2 if onset.month in (6,7,8,9) else .8),
                    'B50':(.9 if onset.month in (6,7,8,9) else .25)*(7 if d in hill else .18)}
                for start,end,event_disease,mult in event_by_d[d]+nationwide:
                    target_disease='J10' if event_disease=='novel_respiratory' else next((c for c,nm in DISEASES.items() if nm==event_disease),None)
                    if target_disease and start<=onset<end: weights[target_disease]*=mult
                disease=rng.choices(codes+['Z00'],[weights[c] for c in codes]+[4])[0]; code=disease if disease in DISEASES else 'Z00'
                profile=population_by_d[d]
                sex=rng.choices(['F','M','X'],weights=[profile['female_population'],profile['male_population'],max(1,(profile['male_population']+profile['female_population'])*.005)],k=1)[0]
                bands=[(0,5,'age_0_4'),(5,18,'age_5_17'),(18,50,'age_18_49'),(50,65,'age_50_64'),(65,101,'age_65_plus')]
                low,high,band=rng.choices(bands,weights=[profile[b[2]] for b in bands],k=1)[0]
                age=rng.randrange(low,high)
                if rng.random()<.01: age=212
                fac=rng.choice(facilities_by_d[d])
                if rng.random()<.005: fac='ORPHAN'
                # A three-week delayed-report episode at one synthetic facility creates a backfill artifact.
                if fac=='F0000' and date(2023,5,1)<=onset<=date(2023,5,21): delay=21
                w.writerow({'encounter_id':eid,'patient_id':f'P{rng.randrange(max(1,target//2)):012d}','facility_id':fac,'district':d,'onset_date':onset,'report_date':onset+timedelta(days=delay),'age_years':age,'sex':sex,'icd10_code':code,'lab_confirmed':int(code!='Z00' and rng.random()<.55),'admitted':int(code!='Z00' and rng.random()<.12),'outcome':rng.choice(['home','admitted','recovered'])})
                count+=1
    (out/'stocks.json').write_text(json.dumps([{'facility_id':x['facility_id'],'district':x['district'],'iv_saline':rng.randrange(0,500),'ns1_kits':rng.randrange(0,300),'ors':rng.randrange(0,400),'antimalarials':rng.randrange(0,150),'occupied_beds':rng.randrange(0,x['beds']+1),'snapshot_date':'2025-12-31'} for x in facilities],indent=2),encoding='utf-8')
    print(f'Generated {count:,} synthetic records with seed {a.seed} under {out}')
if __name__=='__main__': main()




