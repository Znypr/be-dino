--!strict
-- Private-test balance. Prices scale with permanent growth bonuses and potion duration/power.
return table.freeze({
    MaxCrystals=2000000000,
    CrystalCount=64, CrystalRespawnSeconds=90, CrystalValue=3,
    LeapCooldown=60, LeapHorizontalSpeed=72, LeapVerticalSpeed=62, LeapDuration=.7,
    WeatherInterval=600, WeatherDuration=180,
    GrowthCap=8, SpeedCap=2.2,
    RarityFactors={compy=1,triceratops=1.35,tyrannosaurus=1.75,raptor=1,stegosaurus=1.35,ankylosaurus=1.75},
    Auras={
        {id="meadow",name="Meadow Glow",rarity="Common",price=60,growth=1.15,color={98,236,112}},
        {id="tidal",name="Tidal Halo",rarity="Rare",price=240,growth=1.35,color={80,214,255}},
        {id="royal",name="Royal Nova",rarity="Legendary",price=900,growth=1.7,color={180,106,255}},
    },
    Potions={
        {id="speed_common",name="Swift Sip",kind="speed",rarity="Common",duration=300,multiplier=1.2,price=20},
        {id="speed_rare",name="Raptor Rush",kind="speed",rarity="Rare",duration=600,multiplier=1.45,price=65},
        {id="speed_legendary",name="Meteor Sprint",kind="speed",rarity="Legendary",duration=900,multiplier=1.75,price=180},
        {id="growth_common",name="Growth Sip",kind="growth",rarity="Common",duration=300,multiplier=1.25,price=25},
        {id="growth_rare",name="Prime Feast",kind="growth",rarity="Rare",duration=600,multiplier=1.6,price=80},
        {id="growth_legendary",name="Titan Tonic",kind="growth",rarity="Legendary",duration=900,multiplier=2,price=220},
    },
    Weather={
        {id="rain",name="Rain",weight=50,growth=1.25,speed=1,loot=1.1},
        {id="thunder",name="Thunderstorm",weight=30,growth=1.1,speed=1.15,loot=1.4},
        {id="blizzard",name="Blizzard",weight=20,growth=1.4,speed=1.05,loot=1.25},
    },
})
