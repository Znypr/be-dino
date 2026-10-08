--!strict
-- Native placeholders; these are not completed illustrated PNG assets.
local function shape(x,y,w,h,color,radius,rotation) return {x=x,y=y,w=w,h=h,color=color,radius=radius or 0,rotation=rotation or 0} end
return {
    volcano={shape(23,46,54,40,"#734F60",8),shape(33,31,34,30,"#FF8051",6),shape(42,8,16,26,"#FFD16B",8,-15),shape(63,17,12,17,"#FF8051",6,25)},
    aurora={shape(12,30,75,12,"#65F5C6",6,-20),shape(15,48,68,12,"#BFA3FF",6,-20),shape(25,66,53,10,"#C9FFEF",5,-20)},
    quake={shape(9,61,34,18,"#E4BF84",5,-14),shape(57,55,34,18,"#B49A7C",5,14),shape(43,20,10,24,"#FFF0CE",4,20),shape(48,41,10,22,"#FFF0CE",4,-25)},
    bloodmoon={shape(14,14,72,72,"#481C41",36),shape(20,20,60,60,"#FF668F",30),shape(35,29,16,16,"#AD3D70",8),shape(53,50,18,18,"#C74473",9)},
}
