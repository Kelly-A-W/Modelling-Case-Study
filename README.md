
# Current Pricing Model:

The model formulas for hull and third-party liability (TPL) coverage for drones and camera attachments are as follows.

## Hull premium

Let $i$ be a drone in fleet $j$. The **gross hull premium** (GHP) for drone $i$ is:

$$
\text{GHP}(i) = 0.06 \times \text{WeightAdj}(i) \times \text{Value}(i)
$$

where $\text{Value}(i)$ is the value of drone $i$, and $\text{WeightAdj}(i)$ is the weight adjustment factor:

$$
\text{WeightAdj}(i) =
\begin{cases}
1.0 & \text{if drone } i \text{ weighs } 0\text{–}5\text{ kg} \cr
1.2 & \text{if drone } i \text{ weighs } 5\text{–}10\text{ kg} \cr
1.6 & \text{if drone } i \text{ weighs } 10\text{–}20\text{ kg} \cr
2.5 & \text{if drone } i \text{ weighs } > 20\text{ kg}
\end{cases}
$$

> **Note:** $\text{GHP}(i)$ is `NA` if $\text{Value}(i)$ is missing or zero.


## TPL premium

Each drone buys a TPL layer of $\text{Limit}(i)$ in excess of $\text{Excess}(i)$. The TPL premium is priced in two steps.

First, the **base layer premium** (BLP) is the premium for the base limit of £1,000,000 with no excess:

$$
\text{BLP}(i) = 0.02 \times \text{Value}(i)
$$

(Unlike hull, no weight adjustment is applied.)

Second, the base layer premium is scaled to the drone's actual layer by an **increased limit factor** (ILF) taken from a Riebesell curve $R(\cdot)$ (see [The Riebesell curve](#the-riebesell-curve) below):

$$
\text{ILF}(i) = R\big(\text{Limit}(i) + \text{Excess}(i)\big) - R\big(\text{Excess}(i)\big)
$$

The **gross liability premium** (GLP) for drone $i$ is then:

$$
\text{GLP}(i) = \text{BLP}(i) \times \text{ILF}(i)
$$

> **Note:** $\text{GLP}(i)$ is `NA` if $\text{Value}(i)$ is missing or zero.

## Detachable cameras

Let $k$ be a detachable camera, and let $C$ be the set of drones that have a detachable camera and $\text{Value}(i) > 0$. Every camera gets the same hull rate: the highest final hull rate among the drones in $C$:

$$
\text{CamRate} = \max_{i \in C} \big( 0.06 \times \text{WeightAdj}(i) \big)
$$

Since we don't know which drone a camera will be mounted on, it is priced as if it were on the riskiest eligible drone. The camera hull premium (CHP) is:

$$
\text{CHP}(k) = \text{CamRate} \times \text{Value}(k)
$$

> **Note:** $\text{CHP}(k)$ is `NA` if $\text{Value}(k)$ is missing or zero. If no drone has a detachable camera, $\text{CamRate} = 0$ (this is what Excel's `MAXIFS` returns when nothing matches).

## Premium summary

The per-item premiums are summed across the fleet:

$$
\text{Hull} = \sum_i \text{GHP}(i), \qquad
\text{TPL} = \sum_i \text{GLP}(i), \qquad
\text{Camera} = \sum_k \text{CHP}(k)
$$

and the total is $\text{Hull} + \text{TPL} + \text{Camera}$ (`NA` items are skipped). The spreadsheet labels these sums **net** and grosses each one up for brokerage $b$ (30% in the example):

$$
\text{Gross} = \frac{\text{Net}}{1 - b}
$$

## Parameters

| Parameter | Value |
|---|---|
| Hull base rate | 6% |
| TPL base rate | 2% |
| Riebesell base limit $B$ | £1,000,000 |
| Riebesell $z$ | 0.2 |
| Weight adjustments | see $\text{WeightAdj}$ above |

## The Riebesell curve

A **Riebesell curve** is an increased-limit-factor curve used in liability pricing, mostly in European markets. It rests on one assumption:

> Every time the limit doubles, the premium goes up by a fixed factor of $(1 + z)$.

With $z = 0.2$, going from a £1m limit to £2m costs 20% more, going to £4m costs another 20% on top of that, and so on. Each extra £1 of cover is worth less than the one before, because large losses are rarer than small ones.

### Formula

For a base limit $B$ and parameter $z$, the factor for total cover up to $x$ is:

$$
R(x) = \left(\frac{x}{B}\right)^{\log_2(1 + z)}
$$

The workbook implements this as a VBA function (`Module1`):

```vba
Function Riebesell(riebesell_base_limit As Double, riebesell_z As Double, x As Double) As Double
    Riebesell = (x / riebesell_base_limit) ^ Application.Log(1 + riebesell_z, 2)
End Function
```

Key properties:

- $R(B) = 1$: the base limit is priced at exactly the base layer premium.
- $R(2x) = (1 + z) R(x)$: this is the doubling rule. Because $(2x/B)^{\log_2(1+z)} = 2^{\log_2(1+z)} \cdot (x/B)^{\log_2(1+z)} = (1+z) R(x)$.
- $R(0) = 0$ when $z > 0$, so a layer with no excess has $\text{ILF} = R(\text{Limit})$.
- For $0 < z < 1$ the exponent is between 0 and 1, so the curve is increasing and concave. Higher layers cost less per £ of cover.

### Pricing a layer

A layer "$L$ xs $E$" pays losses between $E$ and $E + L$, so its factor is the difference between the curve at the top and the bottom of the layer:

$$
\text{ILF} = R(E + L) - R(E)
$$


## Suggested extensions

### 1. More drones than can fly at once ($N > n$)

Customers may have a large fleet of $N$ drones but warrant that at most $n$ will fly at any one time (`max_drones_in_air`). The $n$ drones with the highest premiums are charged the full rate, and every other drone is charged a fixed £150.

**Method**

**Step 1.** Calculate $\text{GHP}(i)$ and $\text{GLP}(i)$ for each drone as above, and combine them:

$$
P(i) = \text{GHP}(i) + \text{GLP}(i)
$$

**Step 2.** Rank the drones with $\text{Value}(i) > 0$ by $P(i)$, highest first. Let $r(i)$ be drone $i$'s rank, with ties broken by serial number so the result is deterministic.

**Step 3.** Keep the full premium for the top $n$ drones and charge £150 for the rest:

$$
P^{\ast}(i) =
\begin{cases}
P(i) & \text{if } r(i) \le n \cr
150 & \text{if } r(i) > n
\end{cases}
$$

**Step 4.** So that the premium summary can still show hull and TPL separately, split the £150 between them in the same proportions as the drone's full premium:

$$
\text{GHP}^{\ast}(i) = P^{\ast}(i) \times \frac{\text{GHP}(i)}{P(i)}, \qquad
\text{GLP}^{\ast}(i) = P^{\ast}(i) \times \frac{\text{GLP}(i)}{P(i)}
$$

If $N \le n$, every drone ranks in the top $n$, so nothing changes.


### 2. More cameras than can fly at once

Most of the risk to cameras comes when they're in the air, and a camera can only be in the air while it is mounted on a flying drone. So at most

$$
m = \min\big(n, \lvert C \rvert\big)
$$

where $\lvert C \rvert$ is the number of drones that have a detachable camera and a non-zero value (the set $C$ defined under [Detachable cameras](#detachable-cameras)).

cameras can be airborne at once. The $m$ most valuable cameras are charged the full rate, and every other camera is charged a fixed £50.

**Method**

**Step 1.** Rank the cameras with $\text{Value}(k) > 0$ by value, highest first. Let $s(k)$ be camera $k$'s rank, with ties broken by serial number.

**Step 2.** Every camera has the same rate, so ranking by value gives the same order as ranking by premium. Charge the full premium for the top $m$ cameras and £50 for the rest:

$$
\text{CHP}^{\ast}(k) =
\begin{cases}
\text{CamRate} \times \text{Value}(k) & \text{if } s(k) \le m \cr
50 & \text{if } s(k) > m
\end{cases}
$$

If there are $m$ or fewer cameras, nothing changes.



# My Improvements:

1. Flag when information is missing and the drone or camera cannot be priced. 


# Limitations:
1. Note that the extension introduces a "tie-breaking" issue: there may be more than $m$ drones in the top $m$. This will not effect the overall premium value, but it will mean that some of the tied drones will be arbitrarily assigned a base premium while the remaining will have a different premium. Eventhough it makes no difference at the total level, it is important to keep in mind when looking at the drone and camera level. 
2. There is a potential 

# Recomendations:
1. Cap at full premium: as written, a drone whose full premium is under £150 would be charged more for not flying. I'd suggest charging whichever is lower, the full premium or £150 (and likewise £50 for cameras).