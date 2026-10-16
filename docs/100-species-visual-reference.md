# 100 Species visual reference (for the low-poly mesh generator)

Purpose: what each creature really looks like, so generated models are recognisable. Style follows [docs/87](87-vision-and-feel-guide.md). Classes follow BD-231/232 and later owner decisions: Elasmosaurus counts as a normal ground dino, Kentrosaurus is ground, armored = Ankylosaurus, Sauropelta, Styracosaurus.

> Sources: written from established palaeontology reference knowledge (Wikipedia/museum-level descriptions); the live Chrome browsing step was not used in this run, so sizes are approximate. Colours are mostly unknown for real animals; hints are educated guesses. Prompts are under 400 characters. Penguin class is a suggestion (not decided). Secret birds are paused (BD-232).

## Species list check
Shipped ids (Config.SpeciesOrder, 22): all are in the requested list. Requested but NOT shipped yet: Kentrosaurus, Sauropelta, Styracosaurus, Liopleurodon, Archelon, and the secret birds Chicken, Pigeon, Duck, Dodo, Penguin (Chickosaurus is the chicken). Shipped but missing from the list: none.

## Compsognathus (compy)
- Class: Ground
- Real size: ~1 m long, ~3 kg
- Must be recognisable: Tiny biped; long thin tail ~half its length; slim head with pointed snout; 2-fingered small arms; long slender legs; chicken-sized
- Colour hints: Pale green-brown, maybe faint stripes (hypothesised)
- Prompt: `tiny two-legged dino, slim pointed snout, long thin tail, small 2-finger arms, long thin legs, sage green, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, tail, arms, legs

## Velociraptor (raptor)
- Class: Ground
- Real size: ~2 m long, 15 kg, knee-high
- Must be recognisable: Biped; long flat snout; big sickle claw on 2nd toe; stiff straight tail; FEATHERED arms/tail; turkey-sized
- Colour hints: Brown/orange with dark bars; feather plumage
- Prompt: `small feathered raptor, long flat snout, big sickle claw on foot, stiff straight tail, feathered arms, bipedal, rusty orange with dark stripes, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, tail, arms, legs

## Triceratops
- Class: Ground
- Real size: ~9 m, 6-12 t
- Must be recognisable: Quadruped; big bony frill; 2 long brow horns + short nose horn; beak; stocky legs; short tail
- Colour hints: Grey-green/brown, maybe lighter frill
- Prompt: `quadruped, large bony neck frill, two long brow horns and short nose horn, parrot beak, stocky legs, olive green with tan frill, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, frill, horns, tail, legs

## Brachiosaurus
- Class: Ground
- Real size: ~22 m, ~30-40 t
- Must be recognisable: Quadruped; very long neck held UP; front legs longer than hind so back slopes down; small head with high nasal bump; short tail
- Colour hints: Grey/green, plain
- Prompt: `giant quadruped, very long upright neck, front legs longer than back legs so back slopes, small head with nose bump, short tail, soft grey-green, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, neck, head, tail, legs

## Stegosaurus
- Class: Ground
- Real size: ~9 m, 5 t
- Must be recognisable: Quadruped; back arches high at hips; two rows of big diamond plates; 4 tail spikes (thagomizer); tiny head low to ground; short front legs
- Colour hints: Dull green/brown; plates maybe red-orange
- Prompt: `quadruped, high arched back, two rows of big diamond plates, four tail spikes, tiny low head, short front legs, green with orange plates, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, plates, tail, legs

## Tyrannosaurus (T-Rex)
- Class: Ground
- Real size: ~12 m, 8 t
- Must be recognisable: Biped; huge skull and thick jaws; tiny 2-finger arms; heavy tail as counterbalance; horizontal posture
- Colour hints: Brown/olive, lighter belly; some feathers possible
- Prompt: `big biped, huge head with thick jaws and teeth, tiny two-finger arms, thick tail, horizontal posture, olive green, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, jaw, tail, arms, legs

## Ankylosaurus
- Class: Armored
- Real size: ~6-8 m, 6 t
- Must be recognisable: Quadruped; wide low body covered in bony armour plates and studs; big tail club; small triangular horns at head back; wide flat skull
- Colour hints: Brown/grey armour, paler belly
- Prompt: `wide low quadruped, back covered in armour plates and spikes, big round tail club, small horns on head, sand brown, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, armor, tail club, legs

## Parasaurolophus
- Class: Ground
- Real size: ~10 m, 2.5 t
- Must be recognisable: Duck-billed; long curved tube crest sweeping back from the head; walks on 2 or 4 legs; stout tail
- Colour hints: Brown/green; crest could be bright/patterned
- Prompt: `duck-billed dino, long curved tube crest swept back from head, wide flat beak, thick tail, stands on all fours, teal with orange crest, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, crest, tail, legs

## Pachycephalosaurus
- Class: Ground
- Real size: ~4.5 m, 450 kg
- Must be recognisable: Biped; thick domed skull with bony knobs/spikes around the back; short arms; stiff tail
- Colour hints: Brown/grey, pale belly
- Prompt: `biped, thick smooth dome head ringed with small bony knobs, short arms, stiff tail, tan brown with pale dome, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head dome, tail, arms, legs

## Gallimimus
- Class: Ground
- Real size: ~6 m, 450 kg
- Must be recognisable: Biped ostrich-like; toothless beak; long thin neck; large eyes on sides; long legs; stiff tail; small arms
- Colour hints: Tan/brown, maybe feathers
- Prompt: `ostrich-like biped, small toothless beak, long thin neck, long running legs, stiff tail, small arms, sandy yellow, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, neck, head, tail, legs

## Spinosaurus
- Class: Ground
- Real size: ~14 m, 7 t
- Must be recognisable: Giant tall back sail of spines; long narrow crocodile snout; conical teeth; powerful arms with big claws; paddle tail; semi-aquatic
- Colour hints: Brown/orange sail with stripes
- Prompt: `big biped, tall skin sail on back, long narrow crocodile snout, strong clawed arms, paddle-like tail, teal-brown with orange sail, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, sail, tail, arms, legs

## Baryonyx
- Class: Ground
- Real size: ~9 m, 1.5-2 t
- Must be recognisable: Biped; long narrow croc-like snout with nostrils far back; big thumb claw; low crest on snout; long tail
- Colour hints: Brown/green, maybe striped
- Prompt: `biped, long narrow crocodile snout with small crest, big curved thumb claw on strong arms, long tail, olive with dark stripes, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, tail, arms, legs

## Therizinosaurus
- Class: Ground
- Real size: ~10 m, 5 t
- Must be recognisable: Potbelly biped; tiny head, beak; long neck; HUGE scythe claws up to 1 m on long arms; feathery coat; broad hips; short tail
- Colour hints: Fuzzy feathers; brown/cream guess
- Prompt: `potbellied biped, small beaked head on long neck, very long scythe claws on long arms, fluffy feathers, short tail, cream and brown, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, neck, head, arms claws, tail, legs

## Kentrosaurus
- Class: Ground
- Real size: ~4.5 m, 1-2 t
- Must be recognisable: Small stegosaur; narrow plates on front half of back, long paired spikes on back half/hips; shoulder spikes; small head; quadruped
- Colour hints: Green-brown; plates orange
- Prompt: `small quadruped, narrow plates on front half of back and long spikes on hips and tail, tiny low head, green with orange plates and spikes, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, plates, tail spikes, legs

## Sauropelta
- Class: Armored
- Real size: ~5-7 m, 1.5 t
- Must be recognisable: Armoured nodosaur; rows of cone spikes down back; huge long shoulder spikes; no tail club; narrow tube-like head; quadruped
- Colour hints: Brown/reddish; armour paler
- Prompt: `low quadruped, rows of cone bumps on back, big long spikes on shoulders, narrow head, no tail club, reddish brown, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, armor, shoulder spikes, tail, legs

## Styracosaurus
- Class: Armored
- Real size: ~5.5 m, 2.7 t
- Must be recognisable: Quadruped; frill rimmed with 6 long spikes (huge pair at the top); one long nose horn; short brow horns; beak
- Colour hints: Grey-green/brown; frill maybe red
- Prompt: `quadruped, neck frill with six long spikes around its edge, one tall nose horn, parrot beak, stocky legs, tan with red frill, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, frill spikes, horn, tail, legs

## Elasmosaurus
- Class: Ground (normal ground dino per owner)
- Real size: ~10 m, 2 t
- Must be recognisable: Extremely long neck (about half the length); small head; broad body; four paddle flippers; short tail
- Colour hints: Grey-green, lighter belly
- Prompt: `long-necked sea reptile, extremely long neck, small head, wide body, four paddle flippers, short tail, grey-blue, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, neck, head, flippers, tail

## Mosasaurus
- Class: Water
- Real size: ~12-15 m, 15 t
- Must be recognisable: Lizard-like sea reptile; long crocodile jaws with teeth; 4 paddle flippers; long tail with fluke at the end; scaly body
- Colour hints: Dark grey/green back, pale belly
- Prompt: `giant sea lizard, long toothy jaws, four paddle flippers, long tail ending in a fluke fin, scaly body, blue-grey, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, flippers, tail fluke

## Plesiosaurus
- Class: Water
- Real size: ~3.5 m
- Must be recognisable: Small head on long neck; round body; four equal flippers; short tail
- Colour hints: Grey/olive
- Prompt: `sea reptile, small head on a long neck, round body, four equal flippers, short tail, olive blue, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, neck, head, flippers, tail

## Ichthyosaurus
- Class: Water
- Real size: ~2 m
- Must be recognisable: Dolphin-shaped; long pointed beak; huge eye; dorsal fin; two pairs of small flippers; crescent tail fluke
- Colour hints: Dark back, pale belly
- Prompt: `dolphin-shaped sea reptile, long pointed beak, big eye, tall back fin, small flippers, crescent tail, dark blue-grey, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, fins, tail fluke

## Liopleurodon
- Class: Water
- Real size: ~6-7 m
- Must be recognisable: Pliosaur: big short neck, huge crocodile-like head with long teeth; 4 large flippers; short tail
- Colour hints: Dark grey/green, pale belly
- Prompt: `pliosaur sea reptile, huge toothy head on short neck, four large flippers, short tail, slate grey-green, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, flippers, tail

## Archelon
- Class: Water
- Real size: ~4 m, 2 t
- Must be recognisable: Giant sea turtle; leathery ridged shell (not hard); beaked head; long paddle flippers
- Colour hints: Brown/olive shell
- Prompt: `giant sea turtle, domed ridged shell, beaked head, four long paddle flippers, short tail, olive brown, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: shell, head, flippers, tail

## Pteranodon
- Class: Fly
- Real size: ~6 m wingspan
- Must be recognisable: Big wings of skin (bat-like, 4th finger); long toothless beak; tall backward head crest; short tail; no feathers
- Colour hints: Brown/grey; crest red-orange maybe
- Prompt: `flying reptile, huge leathery wings, long toothless beak, tall pointed head crest swept back, short tail, tan with red crest, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head crest, left wing, right wing, legs

## Quetzalcoatlus
- Class: Fly
- Real size: ~10-11 m wingspan, giraffe-tall
- Must be recognisable: Enormous wings; extremely long neck; very long toothless spear beak; small crest; long legs, walks on 4
- Colour hints: Grey/brown; pink guess
- Prompt: `giant flying reptile, huge leathery wings, long neck, extremely long spear beak, long legs, pale grey-pink, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, neck, head, left wing, right wing, legs

## Dimorphodon
- Class: Fly
- Real size: ~1.4 m wingspan
- Must be recognisable: Big blunt head, deep beak, two types of teeth; long tail with diamond tip; leathery wings; small
- Colour hints: Brown/orange
- Prompt: `small flying reptile, big blunt head, deep beak, long thin tail with diamond tip, leathery wings, orange brown, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, left wing, right wing, tail

## Archaeopteryx
- Class: Fly
- Real size: ~0.5 m, 1 kg
- Must be recognisable: Feathered wings with 3 clawed fingers; teeth in beak; long bony feather tail; crow-sized
- Colour hints: Dark/black feathers, light belly guess
- Prompt: `crow-sized feathered dino-bird, wing feathers with finger claws, toothy beak, long feathered tail, dark blue-grey feathers, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, left wing, right wing, tail

## Microraptor
- Class: Fly
- Real size: ~0.8 m
- Must be recognisable: Four wings: feathers on arms AND legs; long diamond-shaped feather tail; small raptor head
- Colour hints: Iridescent glossy black-blue feathers
- Prompt: `small feathered raptor with four wings (arms and legs), long tail feathers with diamond tip, sharp small head, glossy blue-black, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, wings, leg wings, tail

## Chickosaurus (Chicken)
- Class: Ground
- Real size: ~0.5 m
- Must be recognisable: Round body; red comb and wattle; short beak; feathered tail fan; thin legs
- Colour hints: White/brown feathers, red comb
- Prompt: `chicken, round body, red comb on head, small beak, fan tail feathers, thin yellow legs, white, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, comb, tail, legs

## Pigeon
- Class: Ground
- Real size: ~0.3 m
- Must be recognisable: Plump body, small head, short beak, rounded wings, fan tail
- Colour hints: Grey with neck sheen, 2 dark wing bars
- Prompt: `plump pigeon, small head, short beak, rounded wings, fan tail, pink feet, blue-grey, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, wings, tail, legs

## Duck
- Class: Ground
- Real size: ~0.6 m
- Must be recognisable: Wide flat orange bill, round body, short legs, webbed feet, upturned tail
- Colour hints: Mallard: green head, brown breast
- Prompt: `round duck, flat wide orange bill, short legs with webbed feet, little upturned tail, yellow or green-head mallard, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, bill, wings, legs

## Dodo
- Class: Ground
- Real size: ~1 m, 10-20 kg
- Must be recognisable: Huge hooked beak; plump pear body; tiny wings; curly tuft tail; stubby legs
- Colour hints: Grey-brown, yellow feet
- Prompt: `fat dodo bird, large hooked beak, round pear body, tiny wings, curly tail tuft, stubby yellow legs, grey-brown, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, beak, tail, legs

## Penguin
- Class: Water
- Real size: ~1 m (emperor 1.1 m)
- Must be recognisable: Upright; flipper wings; black head and back, white belly; short legs, webbed feet; stiff tail
- Colour hints: Black and white; yellow neck patch (emperor)
- Prompt: `upright penguin, flipper wings, black back, white belly, short orange bill, short webbed feet, black and white, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Parts: body, head, flippers, feet

## Most likely to look wrong in generation
- Therizinosaurus: claws become short; ask for very long scythe claws and a potbelly.
- Spinosaurus / Baryonyx: both turn into a T-Rex; stress the long crocodile snout, and the sail for Spinosaurus.
- Brachiosaurus vs Elasmosaurus necks: sauropod neck goes UP, sea reptile neck is long and low; give front legs longer than hind.
- Kentrosaurus vs Stegosaurus: narrow plates front, long spikes back, much smaller.
- Sauropelta vs Ankylosaurus: no tail club, big shoulder spikes.
- Styracosaurus vs Triceratops: six frill spikes, one nose horn, no big brow horns.
- Pterosaurs (Pteranodon, Quetzalcoatlus, Dimorphodon): wings are skin, not feathers; Quetzalcoatlus needs the long spear beak.
- Microraptor: four wings; Archaeopteryx: toothy beak, clawed wing fingers.
- Mosasaurus / Ichthyosaurus / Liopleurodon: shapes get confused (lizard with fluke, dolphin, short-neck pliosaur).
- Archelon: leathery ridged shell, not a tortoise dome.
- Eyes must stay solid black with a white dot, never hollow.
