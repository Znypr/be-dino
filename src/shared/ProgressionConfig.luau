--!strict
-- Private-test balance. Prices scale with permanent growth bonuses and potion duration/power.
return table.freeze({
    MaxCrystals=2000000000,
    CrystalCount=100, CrystalRespawnSeconds=90, CrystalValue=3,
    LeapCooldown=60, LeapHorizontalSpeed=72, LeapVerticalSpeed=62, LeapDuration=.7,
    WeatherInterval=600, WeatherDuration=180,
    GrowthCap=8, SpeedCap=2.2,
    AccountXPPerLevel=100, AccountMaxLevel=60,
    -- BD-044 PROVISIONAL run crystals (deterministic; the random 5/15/50 crystal box is retired).
    -- Re-tuned 2026-10-13 for 40 eggs per 500 food:
    -- crystals = min(RunCrystalCap, (RunCrystalPerEggHundredths*min(eggs,RunCrystalTierEggs)
    --            + RunCrystalPerExtraEggHundredths*max(0,eggs-RunCrystalTierEggs)) // 100).
    -- 40 eggs (500 food) -> 30, 400 eggs (5,000 food) -> 220 (owner's illustrative 30/220), 500 eggs -> 273; cap 300 bounds it.
    RunCrystalPerEggHundredths=75, RunCrystalTierEggs=40, RunCrystalPerExtraEggHundredths=53, RunCrystalCap=300,
    RandomEggPrice=150,
    ConditionUpgrades={
        {level=1,price=100,requiredLevel=3},{level=2,price=300,requiredLevel=8},
        {level=3,price=800,requiredLevel=16},{level=4,price=1800,requiredLevel=28},
        {level=5,price=4000,requiredLevel=45},{level=6,price=8500,requiredLevel=60},
    },
    Conditions={
        {id="cracked",name="Cracked",stats=.8,hatchChance=.2},
        {id="dirty",name="Dirty",stats=.8,hatchChance=1},
        {id="normal",name="Normal",stats=1,hatchChance=1},
        {id="rainbow",name="Rainbow",stats=1.2,hatchChance=1},
        {id="astra",name="Astra",stats=1.8,hatchChance=1},
    },
    -- BD-045 condition odds, integer weights out of ConditionWeightScale (10,000 = 100%).
    -- Tier 0 is the owner target 50/30/15/4.5/0.5. Tiers 1-6 are a PROVISIONAL monotonic
    -- curve (Cracked/Dirty fall, Normal/Rainbow/Astra rise every tier); not approved balance.
    -- Historical Build 020 (build020-conditions, percent): {20,25,45,9,1},{17,23,47,11,2},
    -- {14,21,48,14,3},{11,19,49,17,4},{8,17,50,20,5},{5,15,51,22,7},{2,12,51,25,10}.
    -- Eggs keep the odds they were rolled with; traitRollVersion records the version.
    ConditionOddsVersion="bd045-conditions-v1",
    ConditionWeightScale=10000,
    ConditionWeights={
        {5000,3000,1500,450,50},
        {4200,2900,2200,600,100},
        {3400,2700,2900,800,200},
        {2600,2400,3600,1050,350},
        {1800,2100,4300,1300,500},
        {1000,1800,4900,1600,700},
        {400,1500,5200,1900,1000},
    },
    EggColors={
        {id="white",name="Cream",weight=5000,rgb={247,234,196}},
        {id="blue",name="Blue",weight=2600,rgb={36,132,211}},
        {id="green",name="Green",weight=1200,rgb={29,175,75}},
        {id="teal",name="Teal",weight=400,rgb={22,170,151}},
        {id="pink",name="Pink",weight=500,rgb={215,72,147}},
        {id="gold",name="Amber",weight=250,rgb={241,160,36}},
        {id="violet",name="Purple",weight=45,rgb={158,80,203}},
        {id="red",name="Red",weight=4,rgb={237,44,33}},
        {id="black",name="Black",weight=1,rgb={29,34,41}},
    },
    RarityFactors={compy=1,triceratops=1.35,tyrannosaurus=1.75,raptor=1,stegosaurus=1.35,ankylosaurus=1.75,archaeopteryx=1,baryonyx=1.35,brachiosaurus=1.35,dimorphodon=1,elasmosaurus=1.75,gallimimus=1,ichthyosaurus=1.35,microraptor=1,mosasaurus=1.75,pachycephalosaurus=1.35,parasaurolophus=1.35,plesiosaurus=1.35,pteranodon=1.35,quetzalcoatlus=1.75,spinosaurus=1.75,therizinosaurus=1.75},
    Auras={
        {id="meadow",name="Meadow Glow",rarity="Common",price=60,growth=1.15,color={98,236,112}},
        {id="tidal",name="Tidal Halo",rarity="Rare",price=240,growth=1.35,color={80,214,255}},
        {id="royal",name="Royal Nova",rarity="Legendary",price=900,growth=1.7,color={180,106,255}},
    },
    Trails={
        {id="white",name="Normal White",rarity="Common",price=0,level=1,speed=1,color={245,247,255},accent={255,255,255},width=.35,lifetime=.6},
        {id="fern",name="Fern Drift",rarity="Common",price=100,level=3,speed=1.02,color={98,236,112},accent={225,255,190},width=.45,lifetime=.7,particles=3},
        {id="tidal",name="Tidal Wake",rarity="Common",price=250,level=6,speed=1.04,color={80,214,255},accent={195,249,255},width=.5,lifetime=.8,particles=4},
        {id="ember",name="Ember Trail",rarity="Rare",price=500,level=10,speed=1.06,color={255,116,62},accent={255,216,107},width=.55,lifetime=.85,particles=5},
        {id="violet",name="Violet Pulse",rarity="Rare",price=900,level=15,speed=1.08,color={180,106,255},accent={255,171,241},width=.6,lifetime=.9,particles=6},
        {id="electric",name="Electric Arc",rarity="Rare",price=1500,level=21,speed=1.10,color={80,243,255},accent={239,255,149},width=.65,lifetime=.95,particles=7},
        {id="frost",name="Frost Comet",rarity="Rare",price=2400,level=28,speed=1.12,color={135,233,255},accent={255,255,255},width=.7,lifetime=1,particles=8},
        {id="solar",name="Solar Flare",rarity="Legendary",price=3600,level=36,speed=1.14,color={255,213,94},accent={255,245,204},width=.75,lifetime=1.05,particles=9},
        {id="nova",name="Nova Ribbon",rarity="Legendary",price=5500,level=45,speed=1.16,color={180,106,255},accent={255,215,115},width=.8,lifetime=1.2,particles=10},
        {id="astra",name="Astra",rarity="Legendary",price=8500,level=60,speed=1.18,color={112,255,205},accent={255,130,232},width=.85,lifetime=1.3,particles=14},
    },
    -- BD-051 + docs/68 PROVISIONAL rotating Potion Shop (one block; owner-approved 2026-10-14: restock every 2 minutes).
    -- Offers derive from the window number (floor(unixSeconds/PeriodSeconds)), so every server agrees and rejoining never rerolls.
    -- Each of the OfferCount slots rolls a rarity from RarityWeights (only rarities that still have unoffered potions), then a
    -- distinct potion of that rarity; the other potions are simply not offered this window (not_offered). Stock is rolled per
    -- offer from StockWeights[rarity] (index = stock, so Epic/Legendary always stock 1). Crystals only.
    PotionShop={
        PeriodSeconds=120, OfferCount=6, MaxStock=3,
        Rarities={"Common","Uncommon","Rare","Epic","Legendary"},
        RarityWeights={Common=50,Uncommon=28,Rare=14,Epic=6,Legendary=2},
        StockWeights={Common={60,30,10},Uncommon={60,30,10},Rare={60,30,10},Epic={1},Legendary={1}},
    },
    -- Prices rise with rarity, power and duration (docs/68). The six pre-catalog ids keep their data and values.
    Potions={
        {id="speed_common",name="Swift Sip",kind="speed",rarity="Common",duration=300,multiplier=1.2,price=20},
        {id="growth_common",name="Growth Sip",kind="growth",rarity="Common",duration=300,multiplier=1.25,price=25},
        {id="loot_common",name="Lucky Sip",kind="loot",rarity="Common",duration=300,multiplier=1.1,price=30},
        {id="speed_uncommon",name="Trail Blazer",kind="speed",rarity="Uncommon",duration=450,multiplier=1.3,price=38},
        {id="growth_uncommon",name="Hearty Brew",kind="growth",rarity="Uncommon",duration=450,multiplier=1.4,price=48},
        {id="speed_rare",name="Raptor Rush",kind="speed",rarity="Rare",duration=600,multiplier=1.45,price=65},
        {id="growth_rare",name="Prime Feast",kind="growth",rarity="Rare",duration=600,multiplier=1.6,price=80},
        {id="loot_rare",name="Treasure Draught",kind="loot",rarity="Rare",duration=600,multiplier=1.25,price=95},
        {id="growth_epic",name="Behemoth Brew",kind="growth",rarity="Epic",duration=750,multiplier=1.8,price=135},
        {id="loot_epic",name="Jackpot Elixir",kind="loot",rarity="Epic",duration=750,multiplier=1.4,price=170},
        {id="speed_legendary",name="Meteor Sprint",kind="speed",rarity="Legendary",duration=900,multiplier=1.75,price=180},
        {id="growth_legendary",name="Titan Tonic",kind="growth",rarity="Legendary",duration=900,multiplier=2,price=220},
    },
    Weather={
        {id="rain",name="Rain",rarity="Common",weight=50,growth=1.25,speed=1,loot=1.1,mutation="dewdrop",chance=.02,icon="rain"},
        {id="thunder",name="Thunderstorm",rarity="Rare",weight=30,growth=1.1,speed=1.15,loot=1.4,mutation="charged",chance=.04,icon="thunder"},
        {id="blizzard",name="Blizzard",rarity="Rare",weight=20,growth=1.4,speed=1.05,loot=1.25,mutation="frost",chance=.04,icon="blizzard"},
        {id="volcano",name="Volcanic Bloom",rarity="Legendary",weight=6,growth=1.2,speed=1,loot=1.65,mutation="ember",chance=.07,icon="volcano"},
        {id="aurora",name="Northern Lights",rarity="Legendary",weight=6,growth=1.3,speed=1.1,loot=1.5,mutation="aurora",chance=.07,icon="aurora"},
        {id="quake",name="Earthquake",rarity="Rare",weight=12,growth=1.1,speed=1,loot=1.4,mutation="seismic",chance=.05,icon="quake"},
        {id="bloodmoon",name="Blood Moon",rarity="Legendary",weight=4,growth=1.15,speed=1.15,loot=1.75,mutation="bloodmoon",chance=.08,icon="bloodmoon"},
    },
    -- Provisional event mutation perks; separate from cosmetic Gold/Diamond fusion.
    EventMutations={
        {id="dewdrop",name="Dewdrop",growth=1.08,speed=1,color={85,216,176}},
        {id="charged",name="Charged",growth=1,speed=1.1,color={255,218,88}},
        {id="frost",name="Frost",growth=1.12,speed=1,color={135,233,255}},
        {id="seismic",name="Seismic",growth=1.15,speed=1,color={220,180,115}},
        {id="ember",name="Ember",growth=1.18,speed=1.04,color={255,116,62}},
        {id="aurora",name="Aurora",growth=1.12,speed=1.08,color={112,255,205}},
        {id="bloodmoon",name="Blood Moon",growth=1.1,speed=1.12,color={255,85,128}},
    },
})
