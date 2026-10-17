---------------------------------------------------------------- 16. BD-615: a run that earned nothing is settled in memory; one that earned anything, or that moves time-driven state, still writes
runScenario("empty-run-no-write", nil, function(server)
    startServices(server)
    local p = connect(server, 1001)
    sleep(2)
    local w0 = M.writes
    local ok, outcome, status = server.Repo.commitRunSettlement(p, "empty-1", 0, nil, 600, nil)
    check("empty-run-no-write: a 0-catch run settles as committed with a zero outcome", ok == true and status == "committed" and type(outcome) == "table" and outcome.eggCount == 0 and outcome.crystals == 0 and outcome.nestCount == 0 and outcome.nestFull == false and outcome.nestCrystals == 0,
        tostring(status) .. " " .. canon(outcome))
    check("empty-run-no-write: and costs no profile write", M.writes == w0, tostring(M.writes - w0))
    check("empty-run-no-write: the client still learns the run was settled", server.PS.get(p, "LastSettledRunId") == "empty-1" and server.PS.get(p, "LastRunEggCount") == 0, tostring(server.PS.get(p, "LastSettledRunId")))
    local ok2, outcome2, status2 = server.Repo.commitRunSettlement(p, "empty-1", 0, nil, 600, nil)
    check("empty-run-no-write: the same run id again is a duplicate (exactly once), still without a write", ok2 == true and status2 == "duplicate" and M.writes == w0, tostring(status2))
    check("empty-run-no-write: nothing about the empty run is stored", profileOf(1001).settledRuns == nil or table.find(profileOf(1001).settledRuns, "empty-1") == nil, "")
    -- a run that earned something writes exactly as before
    local eggsBefore = eggTotals(1001)
    local okFull, outFull, statusFull = server.Repo.commitRunSettlement(p, "full-1", 5, nil, 600, nil)
    check("empty-run-no-write: a 5-catch run still commits with a write and 5 eggs", okFull == true and statusFull == "committed" and M.writes > w0 and eggTotals(1001) == eggsBefore + 5, tostring(statusFull) .. " eggs " .. (eggTotals(1001) - eggsBefore))
    local okFull2, _, statusFull2 = server.Repo.commitRunSettlement(p, "full-1", 5, nil, 600, nil)
    check("empty-run-no-write: and settles once", okFull2 == true and statusFull2 == "duplicate" and eggTotals(1001) == eggsBefore + 5, tostring(statusFull2))
    -- an empty run next to a nest that is still incubating (nothing to advance yet) needs no write
    server.Repo.release(p) disconnect(server, p)
    DATA[keyOf(1001)].eggNests = {{nestId = "nest:seed:1", droppedFromRun = "seed", size = 3, luck = 1, state = "incubating", readyAt = vos.time() + 1000},
        {nestId = "nest:seed:2", droppedFromRun = "seed", size = 3, luck = 1, state = "ready", readyAt = vos.time() - 5}}
    p = connect(server, 1001)
    sleep(2)
    local w1 = M.writes
    server.Repo.commitRunSettlement(p, "empty-2", 0, nil, 600, nil)
    check("empty-run-no-write: an empty run beside a nest that is still incubating needs no write", M.writes == w1, tostring(M.writes - w1))
    -- once that nest has finished incubating, the next empty run must write (the settlement is the tick that moves the queue on)
    sleep(2000)
    local w2 = M.writes
    server.Repo.commitRunSettlement(p, "empty-3", 0, nil, 600, nil)
    check("empty-run-no-write: an empty run after a nest finished incubating keeps its write (it advances the nest queue)", M.writes > w2, tostring(M.writes - w2))
    reportErrors("empty-run-no-write", takeErrors())
end)
