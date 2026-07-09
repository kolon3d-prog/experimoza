cycle_time = 10.0
t = state.t % cycle_time

if t < 2.5:
    fx.constant(math.sin(t * 2.0) * 1500)
    fx.sine(150, period_us=25000)
    fx.spring(500, saturation=2000, dead_band=1000)
    fx.damper(500, saturation=1000, dead_band=0)
elif t < 5.0:
    fx.constant(math.sin(t * 6.0) * 3000 + -state.x * 1500)
    fx.sine(400, period_us=45000)
    fx.spring(1200, saturation=3000, dead_band=500)
    fx.damper(2000, saturation=2000, dead_band=0)
elif t < 7.5:
    fx.constant(math.cos(t * 4.0) * 800 + state.x_velocity * -500)
    fx.sine(800, period_us=12000)
    fx.spring(2000, saturation=4000, dead_band=200)
    fx.damper(4000, saturation=5000, dead_band=0)
else:
    fx.constant(math.sin(t * 1.5) * 2500)
    fx.sine(50, period_us=60000)
    fx.spring(100, saturation=1000, dead_band=2000)
    fx.damper(200, saturation=500, dead_band=0)