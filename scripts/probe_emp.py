import istat_sdmx as s
for f in ["DF_DCSS_EMPLP_1_COM","DF_DCSS_ISTR_LAV_PEN_2_TV_3","183_277_DF_DICA_ASIAUE1P_1","183_1163_DF_DICA_ASIAULP_TERRIFDATA_1"]:
    try:
        d,c=s.structure(f); print("===",f,flush=True)
        for dim,_,cl in d:
            lab=c.get(cl,{}); print("  ",dim,cl,len(lab),"; ".join(f"{k}={v}" for k,v in list(lab.items())[:40])[:700] if dim!="REF_AREA" else "",flush=True)
    except Exception as e: print("===",f,"ERR",e,flush=True)
for f,k in [("DF_DCSS_EMPLP_1_COM","A.048017"),("183_277_DF_DICA_ASIAUE1P_1","A.048017"),("183_1163_DF_DICA_ASIAULP_TERRIFDATA_1","A.048017")]:
    try:
        dims,_=s.structure(f); key=k+"."*(len(dims)-2)
        d=s.data(f,key); print("DATA",f,d.shape,flush=True)
        for col in d.columns:
            if col not in("OBS_VALUE","DATAFLOW") and not col.startswith("NOTE") and d[col].notna().any(): print("   ",col,d[col].value_counts().head(20).to_dict(),flush=True)
    except Exception as e: print("DATA",f,"ERR",str(e)[:200],flush=True)
