"""Light history for the LegiScan states (states/light.py, states/LIGHT.md, states/LEGISCAN.md): an older session is one
LegiScan dataset (a zip of every bill, roll call and person, made weekly; a finished session's never changes), read with
legiscan.py's own dataset_list() and take_dataset() into the scratch folder's legiscan/<session_id>/, where the state's
converter (legiscan_convert.folders()) finds it. One getDatasetList a day per state (kept in data/legiscan/, as
legiscan.py's) and one getDataset per LegiScan session: a handful of queries a state, counted in data/legiscan/usage.json
like every query (the light workflow's runner starts that count afresh: legiscan.py's own count, in the download job's
cache, doesn't see these few dozen; its 300-query margin covers them). No master lists, single bills or supplements."""
import os, sys

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def sessions_from(first, last, step=1):
    """The light sessions, by the first year the converter keys them by: from `first` up to (not including) `last`."""
    return list(range(first, last, step))


def fetch(st, session, data, years=None):
    """Download the regular LegiScan datasets whose first year is in `years` (default: the session's own year) into
    data/legiscan/<session_id>/. True when every one was read."""
    sys.path.insert(0, HERE)
    import legiscan as L
    L.KEY = L.load_key()
    years = set(years or [session])
    try:
        datasets = L.dataset_list(st)
    except L.Stop as e:
        print(f"{st} {session}: {e}", flush=True)
        return False
    if not datasets:
        print(f"{st} {session}: no dataset list", flush=True)
        return False
    wanted = [d for d in datasets if not int(d.get("special") or 0) and int(d["year_start"]) in years]
    if not wanted:
        print(f"{st} {session}: LegiScan lists no regular session starting in {sorted(years)}", flush=True)
        return False
    ok = True
    for ds in sorted(wanted, key=lambda d: int(d["year_start"])):
        folder = os.path.join(data, "legiscan", str(ds["session_id"]))
        meta = {"bills": {}, "session": {k: ds.get(k) for k in ("session_id", "state_id", "year_start", "year_end",
                                                               "session_name", "session_title", "special", "sine_die",
                                                               "prior")}}
        print(f"{st.upper()} {ds['session_name']} (session {ds['session_id']}, {ds['year_start']}-{ds['year_end']})",
              flush=True)
        try:
            got = L.take_dataset(folder, meta, ds)
        except L.Stop as e:
            print(f"  {e}", flush=True)
            return False
        if got is not True:
            ok = False
            continue
        L.write_json(os.path.join(folder, "meta.json"), meta, indent=1)
    return ok
