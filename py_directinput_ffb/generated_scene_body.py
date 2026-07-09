cycle_time = 10.0
t = state.t % cycle_time

if t < 2.5:
    fx.constant(-state.x * 500 + math.sin(t * 2.0) * 800)
    fx.sine(200, period_us=25000)
    fx.spring(500, saturation=1000, dead_band=500)
    fx.damper(1000, saturation=1000, dead_band=0)
elif t < 5.0:
    drift = math.sin(t * 0.5) * 2000
    fx.constant(drift - state.x_velocity * 100)
    fx.sine(600, period_us=45000)
    fx.spring(100, saturation=2000, dead_band=100)
    fx.damper(2000, saturation=3000, dead_band=0)
elif t < 7.5:
    gust = math.sin(t * 8.0) * 4000
    fx.constant(gust + (state.x * -3000))
    fx.sine(1200, period_us=15000)
    fx.spring(2000, saturation=4000, dead_band=200)
    fx.damper(500, saturation=1000, dead_band=0)
else:
    pulse = 9000 if (t % 0.5) < 0.1 else 0
    fx.constant(pulse * (1 if math.sin(t) > 0 else -1))
    fx.sine(3000, period_us=8000)
    fx.spring(5000, saturation=6000, dead_band=100)
    fx.damper(4000, saturation=6000, dead_band=0)