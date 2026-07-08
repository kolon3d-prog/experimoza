cycle_time = 10.0
t = state.t % cycle_time

if t < 0.5:
    fx.constant(0)
    fx.sine(0)
    fx.spring(500)
    fx.damper(500)
elif t < 2.0:
    fx.constant(math.sin(t * 50.0) * 8000)
    fx.sine(4000, period_us=8000)
    fx.spring(1000)
    fx.damper(2000)
elif t < 4.5:
    fx.constant(math.sin(t * 2.0) * 2000 - state.x * 5000)
    fx.sine(1500, period_us=20000)
    fx.spring(4000)
    fx.damper(1000)
elif t < 5.0:
    fx.constant(9500 if t < 4.7 else -9500)
    fx.sine(8000, period_us=5000)
    fx.spring(0)
    fx.damper(5000)
elif t < 8.0:
    fx.constant(-state.x * 3000 + math.sin(t * 10.0) * 4000)
    fx.sine(2000, period_us=12000)
    fx.spring(2000)
    fx.damper(3000)
else:
    fx.constant(state.x * -8000)
    fx.sine(0)
    fx.spring(8000)
    fx.damper(6000)