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
    Trails={
        {id="fern",name="Fern Drift",rarity="Common",price=45,color={98,236,112},accent={225,255,190},width=.45,lifetime=.7},
        {id="tidal",name="Tidal Wake",rarity="Rare",price=180,color={80,214,255},accent={195,249,255},width=.65,lifetime=.95},
        {id="nova",name="Nova Ribbon",rarity="Legendary",price=650,color={180,106,255},accent={255,215,115},width=.8,lifetime=1.2},
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
