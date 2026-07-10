cycle_time = 10.0
t = state.t % cycle_time

if t < 1.0:
    fx.constant(math.sin(t * 20.0) * 8000)
    fx.sine(6000, period_us=8000)
    fx.spring(1000)
    fx.damper(5000)
elif t < 3.0:
    fx.constant(state.x * -5000 + (math.sin(t * 50.0) * 4000))
    fx.sine(2000, period_us=5000)
    fx.spring(5000)
    fx.damper(2000)
elif t < 4.0:
    fx.constant(9000 if (t * 10) % 2 < 1 else -9000)
    fx.sine(9000, period_us=10000)
    fx.spring(0)
    fx.damper(0)
elif t < 6.0:
    fx.constant(math.cos(t * 3.0) * 7000)
    fx.sine(0)
    fx.spring(2000)
    fx.damper(8000)
elif t < 8.0:
    fx.constant(-state.x_velocity * 5000)
    fx.sine(4000, period_us=15000)
    fx.spring(8000)
    fx.damper(1000)
else:
    fx.constant(math.sin(t * 10.0) * 2000 + (10000 if t > 9.5 else 0))
    fx.sine(10000 if t > 9.5 else 0, period_us=5000)
    fx.spring(2000)
    fx.damper(4000)