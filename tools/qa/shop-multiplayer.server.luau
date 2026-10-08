-- Disposable StudioTestService harness. Never package with the game.
-- Edit-time prerequisites: zero-wallet flag and empty earned-only product catalog.
-- Restore Config and remove both harness scripts after the test.
local Test=game:GetService("StudioTestService")
local Players=game:GetService("Players")
local Http=game:GetService("HttpService")
if game.GameId~=0 or game.PlaceId~=0 or Test:GetTestArgs()~="shops-private-v1" then return end
local ended=false
local function finish(result)
    if ended then return end ended=true Test:EndTest(result)
end
task.delay(90,function() finish({passed=false,error="fixture_timeout"}) end)
local ok,result=xpcall(function()
    local Repo=require(game.ServerScriptService.Server.ProfileRepository)
    local deadline=os.clock()+60
    repeat task.wait(.1) until #Players:GetPlayers()==2 or os.clock()>deadline
    assert(#Players:GetPlayers()==2,"two clients did not connect")
    local list=Players:GetPlayers()
    table.sort(list,function(a,b)return a.UserId<b.UserId end)
    local a,b=list[1],list[2]
    repeat task.wait(.1) until (Repo.isLoaded(a) and Repo.isLoaded(b) and a.Character and b.Character) or os.clock()>deadline
    assert(Repo.isLoaded(a) and Repo.isLoaded(b),"profiles not loaded")
    assert(Repo.progression(a).crystals==0 and Repo.progression(b).crystals==0,"ordinary wallets required")
    for i=1,100 do assert(Repo.progressionAction(a,"grant","crystal","fixture-grant-"..i,false,100)) end
    assert(Repo.progression(b).crystals==0,"cross-player grant")
    local bridge=Instance.new("RemoteEvent") bridge.Name="ShopQA" bridge.Parent=game.ReplicatedStorage
    local acknowledgments={}
    bridge.OnServerEvent:Connect(function(p,status)acknowledgments[p]=status end)
    deadline=os.clock()+45
    repeat task.wait(.1) until (acknowledgments[a] and acknowledgments[b]) or os.clock()>deadline
    assert(acknowledgments[a] and acknowledgments[b],"client remote probes timed out")
    assert(Repo.progression(a).crystals==10000 and Repo.progression(b).crystals==0,"client grant or cross-player charge")
    assert(not Repo.progression(a).trails.astra and not Repo.progression(b).trails.astra,"level bypass")
    local statusA,statusB=acknowledgments[a],acknowledgments[b]
    assert(statusA=="level_locked" and statusB=="level_locked","level lock response: "..tostring(statusA).." / "..tostring(statusB))
    local Rewards=require(game.ServerScriptService.Server.RewardMath)
    local compute=Rewards.computeRunReward
    Rewards.computeRunReward=function()return {stacks={},chestCount=0}end
    for i=1,100 do assert(Repo.commitRunSettlement(a,"qa-level-"..i,5000)) end
    Rewards.computeRunReward=compute
    local beforePurchases=Repo.progression(a).crystals
    assert(Repo.progressionAction(a,"buyTrail","astra","fixture-astra"))
    assert(Repo.progressionAction(a,"equipTrail","astra","fixture-equip"))
    assert(Repo.progressionAction(a,"buyPotion","speed_common","fixture-potion"))
    local finished=0
    local outcomes={}
    for i=1,2 do task.spawn(function()
        local success,status=Repo.progressionAction(a,"buyEgg","random","same-token")
        outcomes[i]={success=success,status=status} finished+=1
    end) end
    repeat task.wait(.05) until finished==2
    assert(outcomes[1].success and outcomes[2].success,"purchase race failed")
    assert(Repo.progression(a).crystals==beforePurchases-8500-20-150,"duplicate debit")
    assert(Repo.progression(b).crystals==0 and not Repo.progression(b).trails.astra,"profile leakage")
    assert(#Http:JSONDecode(a:GetAttribute("ChestQueueJson"))==1,"duplicate egg")
    assert(#Http:JSONDecode(b:GetAttribute("ChestQueueJson"))==0,"cross-player queue")
    task.wait(1.2)
    local speedA=a:GetAttribute("SpeedMultiplier")
    local speedB=b:GetAttribute("SpeedMultiplier")
    return {passed=true,players={a.UserId,b.UserId},wallets={Repo.progression(a).crystals,0},queues={1,0},
        beforePurchases=beforePurchases,
        actualClients=true,remoteStatuses={statusA,statusB},race=outcomes,
        levels={a:GetAttribute("AccountLevel"),b:GetAttribute("AccountLevel")},
        speedMultipliers={speedA,speedB},persistent=false}
end,debug.traceback)
finish(if ok then result else {passed=false,error=result})
