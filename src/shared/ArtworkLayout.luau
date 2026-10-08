--!strict
-- Normalized coordinates in a square thumbnail. Adjust here without regenerating PNGs.
return {
    ringPosition = Vector2.new(.5,.62),
    ringSize = .70, -- inset prevents transparent fringe/outer glow from reaching card edges
    ringSplitY = .62,
    centerpiecePosition = Vector2.new(.5,.42),
    centerpieceSize = .62,
    bottlePosition = Vector2.new(.5,.5),
    bottleSize = .94,
    symbolPosition = Vector2.new(.5,.65),
    symbolSize = .30,
    mutationSize = .94,
    catches = {{.28,.72,-18},{.5,.5,12},{.72,.28,-12}},
    catchesSize = .42,
}
