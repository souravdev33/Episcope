"""Small-data evaluation/export stage. Ground truth file is deliberately never read."""
import argparse, json
from pathlib import Path
import numpy as np

DISEASES=['dengue','diarrhoea','influenza','malaria']
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',default='data/lake'); ap.add_argument('--output',default='data/serving'); a=ap.parse_args()
    from pyspark.sql import SparkSession, functions as F
    spark=SparkSession.builder.appName('EpiScopeAnalytics').master('local[*]').config('spark.sql.shuffle.partitions','8').getOrCreate()
    rows=spark.read.parquet(str(Path(a.input)/'gold'/'weekly')).toPandas()
    pop=spark.read.option('header',True).option('inferSchema',True).csv(str(Path(a.input).parent/'input'/'population.csv')).toPandas().set_index('district').population.to_dict()
    # Sum records if duplicate weekly partitions exist; this stage only sees aggregated gold.
    g=rows.groupby(['district','disease','epi_year','epi_week'],as_index=False).agg(cases=('cases','sum'),admissions=('admissions','sum'))
    out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    alerts=[]; forecasts=[]; heat=[]; alloc=[]; latest={}
    for (district,disease),x in g.groupby(['district','disease']):
        x=x.sort_values(['epi_year','epi_week']).copy(); vals=x.cases.to_numpy(dtype=float)
        x['baseline']=x.cases.shift(1).rolling(8,min_periods=4).mean()
        x['sd']=x.cases.shift(1).rolling(8,min_periods=4).std().fillna(1).clip(lower=1)
        x['z']=(x.cases-x.baseline)/x.sd
        x['alert']=x.z>=2.5
        for _,r in x.iterrows():
            heat.append({'district':district,'disease':disease,'year':int(r.epi_year),'week':int(r.epi_week),'cases':int(r.cases)})
            if bool(r.alert): alerts.append({'district':district,'disease':disease,'year':int(r.epi_year),'week':int(r.epi_week),'observed':int(r.cases),'expected':round(float(r.baseline),1),'score':round(float(r.z),2),'method':'8-week EARS-like z-score'})
        last=x.iloc[-1]; base=float(np.nanmean(vals[-8:])) if len(vals) else 0
        for h in range(1,5):
            # Seasonal-naive annual lag where available; small finite-sample fallback.
            annual=vals[-52+h-1] if len(vals)>=52+h else base
            # modest seasonal-naive blend; weather covariates are not present in this prototype.
            pred=max(0,round(.75*float(annual)+.25*base))
            forecasts.append({'district':district,'disease':disease,'horizon':h,'mean':pred,'lower80':max(0,round(pred-1.28*np.sqrt(pred+1))),'upper80':round(pred+1.28*np.sqrt(pred+1))})
        latest[(district,disease)]=int(last.cases)
    # Planning snapshot: simple deterministic weighted marginal benefit rule, stated as a heuristic.
    cases_by_d={d:sum(v for (dd,_),v in latest.items() if dd==d) for d in pop}
    total_budget=200000
    demand={d:max(1,int(cases_by_d.get(d,0)*.2+pop[d]/100000)) for d in pop}
    weights={d:1.0+(0.5 if d in ['Bandarban','Rangamati','Khagrachhari'] else 0) for d in pop}
    total=sum(demand.values())
    for d in pop:
        need=demand[d]; fair=int(total_budget*pop[d]/sum(pop.values())*.15)
        recommended=min(need,max(fair,int(total_budget*weights[d]*need/sum(weights[k]*demand[k] for k in pop))))
        alloc.append({'district':d,'demand_units':need,'current_stock_units':max(0,int(need*.35)),'recommended_units':recommended,'budget_cost':recommended,'population':pop[d]})
    allocations=[]
    for budget in [50000,100000,150000,200000,250000]:
        funded=sum(min(x['demand_units'],int(budget*x['demand_units']/total)) for x in alloc)
        allocations.append({'budget':budget,'units_funded':funded,'equity_floor_share':.15})
    calendar=[{'division':'National','disease':d,'prepare_month':'May','campaign_month':'June','rationale':'seasonal planning hypothesis; validate with public surveillance and climate data'} for d in DISEASES]
    # Suppress any count in [1,4]. Remove district totals where suppression would permit subtraction.
    for arr,key in [(heat,'cases')]:
        for r in arr:
            if 0<int(r[key])<5: r[key]=None; r['suppressed']=True
            else: r['suppressed']=False
    for r in forecasts:
        for k in ('mean','lower80','upper80'):
            if 0<r[k]<5: r[k]=None
    payload={'generated_at':__import__('datetime').datetime.now().astimezone().isoformat(),'synthetic':True,'districts':list(pop),'diseases':DISEASES,
      'heatmap':heat,'alerts':alerts,'forecasts':forecasts,'allocations':alloc,'budget_curve':allocations,'calendar':calendar,
      'quality':json.loads((Path(a.input)/'gold'/'quality_report.json').read_text(encoding='utf-8'))}
    (out/'dashboard.json').write_text(json.dumps(payload,allow_nan=False),encoding='utf-8')
    print(f"Exported {len(g)} district-disease-weeks, {len(alerts)} threshold flags. Metrics require labeled backtest; flags are not validated outbreak alerts.")
    spark.stop()
if __name__=='__main__': main()
