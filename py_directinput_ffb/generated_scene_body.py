# The high-speed straight-line instability and vibration of a drag racing car at launch and terminal speed.
cycle_time = 10.0
t = state.t % cycle_time

if t < 1.2:
    fx.constant(force=clamp(4000 + (t * 2000) + (state.x * 2000), -8000, 8000))
    fx.sine(magnitude=clamp(t * 3000, 0, 8000), period_us=20000)
    fx.spring(coefficient=500, saturation=2000, dead_band=500)
    fx.damper(coefficient=1000, saturation=4000, dead_band=0)
elif t < 3.5:
    fx.constant(force=3000 + math.sin(t * 10) * 2500)
    fx.sine(magnitude=4000, period_us=50000)
    fx.spring(coefficient=200, saturation=1000, dead_band=1000)
    fx.damper(coefficient=2000, saturation=3000, dead_band=0)
elif t < 6.0:
    fx.constant(force=-2000 + (state.x * -4000))
    fx.sine(magnitude=6000, period_us=30000)
    fx.spring(coefficient=100, saturation=1000, dead_band=2000)
    fx.damper(coefficient=3000, saturation=5000, dead_band=0)
elif t < 8.5:
    fx.constant(force=4000 * math.cos(t * 5))
    fx.sine(magnitude=2000, period_us=60000)
    fx.spring(coefficient=800, saturation=3000, dead_band=500)
    fx.damper(coefficient=1500, saturation=4000, dead_band=0)
else:
    fx.constant(force=-6000 + ((t - 8.5) * 8000))
    fx.sine(magnitude=8000, period_us=15000)
    fx.spring(coefficient=1200, saturation=4000, dead_band=0)
    fx.damper(coefficient=4000, saturation=6000, dead_band=0)