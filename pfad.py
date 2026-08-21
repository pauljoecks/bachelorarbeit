# Eingaben:
# points: Pfadpunkte [x,y]
# beta: Hotspot-Verstärkung
# aL, aQ: Längs-/Querschrumpfungsgewichte
# r0, Dnorm, lambda_cool: thermische Modellparameter
# xc: Bauteilschwerpunkt
# Lref: charakteristische Länge

segments = []

t = 0.0
for i in range(N):
    p0 = points[i]
    p1 = points[i+1]

    e = p1 - p0
    ds = norm(e)
    tangent = e / ds
    normal = np.array([-tangent[1], tangent[0]])
    xi = 0.5 * (p0 + p1)

    t_mid = t + 0.5 * ds  # normierte Zeit, wenn v konstant
    theta = atan2(tangent[1], tangent[0])

    segments.append({
        "ds": ds,
        "t": t_mid,
        "xi": xi,
        "tangent": tangent,
        "normal": normal,
        "theta": theta
    })

    t += ds

# Hotspot H_i
H = np.zeros(N)

for i in range(N):
    for j in range(i):
        dt = segments[i]["t"] - segments[j]["t"]
        d = norm(segments[i]["xi"] - segments[j]["xi"])

        sigma2 = r0**2 + 2 * Dnorm * dt

        w = np.exp(-d**2 / (2 * sigma2)) * np.exp(-lambda_cool * dt)

        H[i] += segments[j]["ds"] * w

Hhat = H / (np.max(H) + 1e-12)

# Amplitudenfaktor
A = np.array([
    segments[i]["ds"] * (1 + beta * Hhat[i])
    for i in range(N)
])

# Kennwert A
K_A = np.sum(A)

# Kennwert B
K_Bx = 0.0
K_By = 0.0

# Kennwert C
K_C = np.zeros((2,2))

for i in range(N):
    tvec = segments[i]["tangent"]
    nvec = segments[i]["normal"]

    K_C += A[i] * (
        aL * np.outer(tvec, tvec)
        + aQ * np.outer(nvec, nvec)
    )

    ex = np.array([1,0])
    ey = np.array([0,1])

    K_Bx += A[i] * (
        aL * np.dot(tvec, ex)**2
        + aQ * np.dot(nvec, ex)**2
    )

    K_By += A[i] * (
        aL * np.dot(tvec, ey)**2
        + aQ * np.dot(nvec, ey)**2
    )

eigvals, eigvecs = np.linalg.eigh(K_C)

# größte zuerst
idx = np.argsort(eigvals)[::-1]
eigvals = eigvals[idx]
eigvecs = eigvecs[:, idx]

lambda1, lambda2 = eigvals
v1 = eigvecs[:,0]

K_aniso = abs(K_Bx - K_By) / (K_Bx + K_By + 1e-12)

# Kennwert D
K_D_mean = np.sum([segments[i]["ds"] * Hhat[i] for i in range(N)]) / \
           (np.sum([seg["ds"] for seg in segments]) + 1e-12)
K_D_95 = np.percentile(Hhat, 95)

# Kennwert E
Mx = 0.0
My = 0.0

for i in range(N):
    xi = segments[i]["xi"]
    dx, dy = xi - xc

    Mx += A[i] * dy
    My += A[i] * dx

denom = np.sum(A) * Lref + 1e-12

Mx_hat = Mx / denom
My_hat = My / denom
K_E = np.sqrt(Mx_hat**2 + My_hat**2)