# NY experiment results

## exp1_ny_parcel

- Sweep parameter: **num_parcels** (Number of Parcels |Γ|)
- Sweep points: [500, 2000, 5000, 10000, 20000]
- Algorithms: ['capa', 'greedy', 'basegta', 'impgta', 'mra', 'ramcom', 'rlcapa']
- Details: [exp1_ny_parcel/README.md](exp1_ny_parcel/README.md)

### Total Revenue

| num_parcels | capa | greedy | basegta | impgta | mra | ramcom | rlcapa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 500 | 1317.54 | 362.45 | 1334.71 | 1297.65 | 452.49 | 499.49 | 1592.79 |
| 2000 | 5736.95 | 2418.85 | 5564.89 | 5392.77 | 3642.99 | 3722.86 | 6310.65 |
| 5000 | 14624.23 | 7281.19 | 13998.60 | 14202.14 | 9727.51 | 10538.23 | 16086.65 |
| 10000 | 27560.34 | 12066.23 | 26602.55 | 27112.95 | 16007.82 | 19413.71 | 30316.37 |
| 20000 | 48965.33 | 14760.35 | 51131.35 | 53890.53 | 21270.21 | 29687.26 | 66803.03 |

## exp2_ny_couriers

- Sweep parameter: **local_couriers** (Number of Local Couriers |C|)
- Sweep points: [100, 200, 300, 400, 500]
- Algorithms: ['capa', 'greedy', 'basegta', 'impgta', 'mra', 'ramcom', 'rlcapa']
- Details: [exp2_ny_couriers/README.md](exp2_ny_couriers/README.md)

### Total Revenue

| local_couriers | capa | greedy | basegta | impgta | mra | ramcom | rlcapa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | 10238.03 | 1386.39 | 13609.14 | 13794.39 | 2030.72 | 5675.57 | 15353.86 |
| 200 | 11120.70 | 2321.65 | 13955.87 | 13841.65 | 3559.85 | 6340.55 | 15351.46 |
| 300 | 11453.88 | 2801.30 | 14067.45 | 14299.24 | 4338.62 | 6468.34 | 15962.64 |
| 400 | 11871.22 | 3539.77 | 13879.13 | 14061.35 | 4707.91 | 7054.75 | 15781.67 |
| 500 | 11729.52 | 3854.17 | 14232.14 | 13969.21 | 5243.61 | 7185.86 | 15655.35 |

## exp3_ny_radius

- Sweep parameter: **service_radius** (Service Radius (km))
- Sweep points: [0.5, 1, 1.5, 2, 2.5]
- Algorithms: ['capa', 'greedy', 'basegta', 'impgta', 'mra', 'ramcom', 'rlcapa']
- Details: [exp3_ny_radius/README.md](exp3_ny_radius/README.md)

### Total Revenue

| service_radius | capa | greedy | basegta | impgta | mra | ramcom | rlcapa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.5 | 11210.05 | 2379.73 | 14099.50 | 14124.31 | 3283.93 | 6373.39 | 15912.48 |
| 1 | 11299.62 | 2252.16 | 13995.61 | 14135.26 | 3244.94 | 6331.95 | 15861.51 |
| 1.5 | 11084.82 | 2285.28 | 13451.53 | 13166.85 | 3428.19 | 6406.89 | 14796.68 |
| 2 | 11107.49 | 2270.98 | 13865.47 | 13921.04 | 3227.32 | 6384.28 | 15726.50 |
| 2.5 | 11310.80 | 2239.74 | 13829.95 | 13957.61 | 3489.65 | 6295.19 | 15717.88 |

## exp4_ny_platforms

- Sweep parameter: **platforms** (Number of Platforms)
- Sweep points: [2, 4, 8, 12, 16]
- Algorithms: ['capa', 'greedy', 'basegta', 'impgta', 'mra', 'ramcom', 'rlcapa']
- Details: [exp4_ny_platforms/README.md](exp4_ny_platforms/README.md)

### Total Revenue

| platforms | capa | greedy | basegta | impgta | mra | ramcom | rlcapa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 7925.47 | 2222.24 | 10105.69 | 9694.38 | 3297.62 | 4460.15 | 11116.26 |
| 4 | 11280.38 | 2368.10 | 13929.81 | 14023.30 | 3405.27 | 6695.22 | 15755.42 |
| 8 | 15141.02 | 2188.81 | 18706.01 | 19090.22 | 3369.43 | 9000.68 | 21075.83 |
| 12 | 17514.21 | 2312.44 | 21128.48 | 21470.84 | 3417.53 | 11063.76 | 23662.64 |
| 16 | 19350.95 | 2401.52 | 22854.21 | 23462.29 | 3384.64 | 12717.47 | 25808.52 |

## exp6_ny_capacity

- Sweep parameter: **courier_capacity** (Courier Capacity)
- Sweep points: [5, 10, 15, 20, 25]
- Algorithms: ['capa', 'greedy', 'basegta', 'impgta', 'mra', 'ramcom', 'rlcapa']
- Details: [exp6_ny_capacity/README.md](exp6_ny_capacity/README.md)

### Total Revenue

| courier_capacity | capa | greedy | basegta | impgta | mra | ramcom | rlcapa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 9677.76 | 803.18 | 12571.57 | 12614.46 | 1481.00 | 4745.68 | 13908.19 |
| 10 | 10975.79 | 2313.60 | 14079.14 | 14143.53 | 3382.97 | 6164.74 | 15991.79 |
| 15 | 11832.21 | 3355.42 | 14186.30 | 14179.05 | 4758.22 | 7493.23 | 15604.93 |
| 20 | 12860.30 | 4394.36 | 14214.50 | 14656.19 | 6003.66 | 8594.00 | 16824.05 |
| 25 | 13408.81 | 5020.47 | 14529.54 | 14848.86 | 6963.96 | 9111.91 | 17312.48 |

## exp5_ny_default

- Default-config comparison.
- Algorithms: ['capa', 'greedy', 'basegta', 'impgta', 'mra', 'ramcom', 'rlcapa']
- Details: [exp5_ny_default/README.md](exp5_ny_default/README.md)

### Fixed Configuration (highlights)


### Total Revenue

| algorithm | TR | CR | BPT |
| --- | --- | --- | --- |
| capa | 11009.31 | 0.482000 | 0.008403 |
| greedy | 2231.26 | 0.102000 | 0.002667 |
| basegta | 14144.50 | 0.514600 | 0.011906 |
| impgta | 13981.21 | 0.493400 | 0.072461 |
| mra | 3246.80 | 0.147800 | 1.0064 |
| ramcom | 6218.07 | 0.281800 | 0.010330 |
| rlcapa | 15558.95 | 0.566060 | 0.002267 |
