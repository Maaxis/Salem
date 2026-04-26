# Salem's flavor text

import random
import re

HackerBongoCat = "<a:HackerBongoCat:1340904279577329676>"
BLEHH_CAT = "<:BLEHH_CAT:1340904028522938380>"
cat_whaaa = "<:cat_whaaa:1340902363896221708>"
kitty_blush_knife = "<:kitty_blush_knife:1272112299355668520>"
SleepyCat = "<a:SleepyCat:1340900214009106462>"
catleave = "<a:catleave:1340901568823689307>"
yaycat = "<:yaycat:1340922271778209865>"
catloading = "<:catloading:1340922339260370964>"
blushy_cat = "<:blushy_cat:1340904310111998095>"
CATHYPE = "<a:CATHYPE:1340922373779488839>"
cat_spook = "<:cat_spook:1340901665997455392>"
thatghostface = "<:thatghostface:1337936377991528448>"
floorcatspin = "<a:floorcatspin:1340922413164265493>"
Cat_Bruh = "<a:Cat_Bruh:1340909080478482462>"
jammers = "<a:jammers:1340901707995025558>"
bunnyu = "<:bunnyu:1340901781848330323>"
SkateboardingKitty = "<a:SkateboardingKitty:1340901633755844709>"
Cute_Cat = "<:Cute_Cat:1272112194573570103>"
catJAM = "<a:catJAM:1340902290906677329>"
CatBounce = "<a:CatBounce:1340900121688412281>"
blackcat_paw = "<a:blackcat_paw:1340899837025058818>"
BlackCat = "<:BlackCat:1340900260418945089>"
cool_cat = "<:cool_cat:1340903281337307167>"
catpffft = "<a:catpffft:1198454041148133416>"
bunny_judge = "<:bunny_judge:1340901752874074152>"
cat_wtf = "<:cat_wtf:1272112115775442953>"
CatMelm = "<:CatMelm:1340900291012333568>"
sulking = "<:sulking:1340902902415233045>"
KITTYCLAPS = "<a:KITTYCLAPS:1340900555039703041>"
blacknod = "<a:blacknod:1340900164256399434>"
Hyper_Popper = "<a:Hyper_Popper:1340903334655033475>"
kitty_blush = "<:kitty_blush:1272112151900979211>"
kirbyreed = "<:kirbyreed:1347074560478154806>"
uhhuh = "<:uhhuh:1350174871161929770>"
mockingcat = "<:mockingcat:1336787940176691271>"
catwant = "<:catwant:1354886784961482923>"
isaidno = "<:isaidno:1354886816750239845>"
catNOO = "<a:catNOO:1340903925900902471>"
cattogun = "<:cattogun:1272112235078090833>"
cute2 = "<a:cute2:1340902809935286356>"

happy_kaomojis = ["☆\\*:.｡.o(≧▽≦)o.｡.:\\*☆",
                  "്ദി(｡•̀ ,<)~✩‧₊",
                  "♡⸜(˶˃ ᵕ ˂˶)⸝♡",
                  "˖ ࣪‧₊˚⋆✩٩(ˊᗜˋ\\*)و ✩",
                  "ฅ^>⩊<^ ฅ",
                  "＼(≧▽≦)／",
                  "ヽ(≧◡≦)八(o^ ^o)ノ",
                  "(ﾉ>ω<)ﾉ :｡･:\\*:･ﾟ’★,｡･:\\*:･ﾟ’☆",
                  "٩(◕‿◕｡)۶",
                  "(≧▽≦)",
                  "(´∀｀)✧",
                  "(ノ°∀°)ノ✧\\*:･ﾟ✧",
                  "(ﾉ^ヮ^)ﾉ\\*:・ﾟ✧",
                  "(ﾉ◕ヮ◕)ﾉ:・゚✧",
                  "(ฅ^•ﻌ•^ฅ)",
                  "(≧∇≦)/"]

output_happy = [HackerBongoCat, yaycat, CATHYPE, Cute_Cat, CatBounce, BlackCat, thatghostface, kirbyreed, catwant]
output_excited = [floorcatspin, SkateboardingKitty, catJAM, jammers, CATHYPE, KITTYCLAPS, blacknod, Hyper_Popper]
output_laughter = [mockingcat]
output_love = [kitty_blush, blackcat_paw, cute2]
output_smug = [cool_cat, BLEHH_CAT, catpffft, blushy_cat, bunnyu, kitty_blush, thatghostface, kirbyreed]
output_confused = [cat_whaaa, cat_wtf, CatMelm, catloading]
output_shocked = [cat_spook, cat_whaaa, cat_wtf]
output_sad = [catleave, sulking]
output_angry = [isaidno, catNOO, cattogun, kitty_blush_knife, bunny_judge, uhhuh]


def random_happy():
	happy = happy_kaomojis + output_happy + output_excited + output_love
	return random.choice(happy)


# ---------------- flavor text defined here
bot_name = "Salem the KITTY of CHAOS (ﾉ≧∀≦)ﾉ"
generic_error_msg = f"{cat_whaaa} WHOOPSIE-DAISY! Something went wrong and it's probably not your fault! Let me get the hoomans to look into this~ {HackerBongoCat}✨"
pause_msg = f"I'm taking a little catnap right now while my owner tinkers with some stuff, try again later... {SleepyCat}"
load_msg = f"One sec, this takes all 3 brain cells...{catloading}"
new_alliance_msg = f"WOAH, NEW ALLIANCE THREAD DETECTED {random_happy()} Let's make sure the whole gang is here ;3"
confessional_notif = [
	"YIPPEE! Board confessional!",
	"<- me when someone posts a confessional",
	"OMG edgic contender rising! :star_struck:",
	f"ASDFJKL;AAH CONFESSIONAL!!!! *Whisker wiggle of excitement*",
	"Back in my day we played ORGs by carrier pigeon. Be thankful for your board confessionals!",
	"TEA ALERT WEE WOO WEE WOO",
	"1 like = 1 tuna saved... for me, later",
	"A new confessional is up, and Goodreads has some RAVING reviews about it!",
	"STOP! You have been visited by the <:thatghostface:1337936377991528448> emoji! Like this confessional or she’ll summon an army of Salems for a tuna heist of your pantry in EPIC proportions.",
	"VIEWER CONTENT VIEWER CONTENT VIEWER CONTENT"
]
