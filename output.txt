cycle_time = 10.0
t = state.t % cycle_time

# The tractor struggle: plunging through deep, sucking, uneven mire.
# Transitions from light wet slip, to heavy drag, to sudden sharp ruts.

if t < 2.0:
    # Slippery, light slush: oscillating resistance as tires hunt for grip
    fx.constant(math.sin(t * 3.0) * 1500)
    fx.sine(1500, period_us=25000)
    fx.spring(500, saturation=2000, dead_band=500)
    fx.damper(2000, saturation=3000, dead_band=0)

elif t < 5.0:
    # Deep, heavy mud: the wheel thickens and drags, pulling to one side as the tire catches
    drag = -state.x * 4000 + math.sin(t * 0.5) * 3000
    fx.constant(drag)
    fx.sine(3000, period_us=60000)
    fx.spring(2000, saturation=5000, dead_band=0)
    fx.damper(7000, saturation=8000, dead_band=0)

elif t < 7.5:
    # Sudden sharp ruts: violent rhythmic jolts as the tractor hits embedded rocks/clumps
    impact = 9000 if (int(t * 10) % 3 == 0) else -state.x * 1000
    fx.constant(impact)
    fx.sine(5000, period_us=12000)
    fx.spring(1000, saturation=3000, dead_band=100)
    fx.damper(4000, saturation=4000, dead_band=0)

else:
    # Breaking free: the mud releases, wheel tension oscillates and fades to a light hum
    release = math.sin(t * 10.0) * 2000
    fx.constant(release)
    fx.sine(800, period_us=45000)
    fx.spring(3000, saturation=4000, dead_band=200)
    fx.damper(1000, saturation=2000, dead_band=0)