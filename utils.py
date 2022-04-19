
#[(1,33.2,44.3,567.5,34), (), (), ...]
def deter_region(coors):
    if not coors:
        return [0, 0, 0, 0, 0]
    for num in range(len(coors)):
        coors[num] = coors[num].split(",")
        for i in range(5):
            coors[num][i] = float(coors[num][i])
        coors[num][0] = int(coors[num][0])
        coors[num][3] += coors[num][1]
        coors[num][4] += coors[num][2]
    ltx = min(coors[i][1] for i in range(len(coors)))
    lty = min(coors[i][2] for i in range(len(coors)))
    rbx = max(coors[i][3] for i in range(len(coors)))
    rby = max(coors[i][4] for i in range(len(coors)))
    return [int(coors[0][0]), ltx, lty, rbx, rby]
