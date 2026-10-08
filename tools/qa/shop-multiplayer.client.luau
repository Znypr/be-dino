-- Installed temporarily only in the unpublished QA copy.
if game.GameId~=0 or game.PlaceId~=0 then return end
local bridge=game.ReplicatedStorage:WaitForChild("ShopQA",60)
if not bridge then return end
local remote=game.ReplicatedStorage:WaitForChild("BeDinoRemotes"):WaitForChild("ProgressionAction")
local status="missing_response"
game.ReplicatedStorage.BeDinoRemotes.ProgressionResult.OnClientEvent:Connect(function(token,_,result)
    if token=="client-locked" then status=result end
end)
remote:FireServer("grant","crystal","client-grant",false,100000)
task.wait(.6)
remote:FireServer("buyTrail","astra","client-locked",false)
local deadline=os.clock()+10
repeat task.wait(.1) until status~="missing_response" or os.clock()>deadline
bridge:FireServer(status)
