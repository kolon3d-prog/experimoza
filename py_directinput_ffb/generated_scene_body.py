cycle_time = 10.0
t = state.t % cycle_time

if t < 2.0:
    fx.constant(math.sin(t * 3.14) * 4000)
    fx.sine(1500, period_us=25000)
    fx.spring(2000)
    fx.damper(500)
elif t < 4.0:
    fx.constant(-state.x * 5000 + math.sin(t * 20.0) * 2000)
    fx.sine(3000, period_us=12000)
    fx.spring(5000)
    fx.damper(3000)
elif t < 6.0:
    pulse = 9000 if (t * 10) % 2 < 1 else -9000
    fx.constant(pulse)
    fx.sine(0)
    fx.spring(500)
    fx.damper(1000)
elif t < 8.0:
    sway = math.sin(t * 5.0) * 7000
    fx.constant(sway - state.x_velocity * 2000)
    fx.sine(500, period_us=50000)
    fx.spring(1000)
    fx.damper(4000)
else:
    fx.constant(-state.x * 8000)
    fx.sine(4000, period_us=8000)
    fx.spring(8000)
    fx.damper(6000)