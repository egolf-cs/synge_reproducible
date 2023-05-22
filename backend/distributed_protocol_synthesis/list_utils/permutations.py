from pprint import pprint

def permutations(iterable, r=None):
    # permutations('ABCD', 2) --> AB AC AD BA BC BD CA CB CD DA DB DC
    # permutations(range(3)) --> 012 021 102 120 201 210
    pool = tuple(iterable)
    n = len(pool)
    r = n if r is None else r
    if r > n:
        return
    indices = list(range(n))
    cycles = list(range(n, n-r, -1))
    yield tuple(pool[i] for i in indices[:r])
    while n:
        for i in reversed(range(r)):
            cycles[i] -= 1
            if cycles[i] == 0:
                indices[i:] = indices[i+1:] + indices[i:i+1]
                cycles[i] = n - i
            else:
                j = cycles[i]
                indices[i], indices[-j] = indices[-j], indices[i]
                yield tuple(pool[i] for i in indices[:r])
                break
        else:
            return

def permutation_dicts(it):
    perms = permutations(it)
    for it_pr in perms:
        if it == list(it_pr):
            continue
        perm_dict = dict(zip(it, it_pr))
        yield perm_dict


def apply_stateperm_var(perm, var, proc):
    (p,a,q) = var
    if p in perm:
        p = perm[p]
    if q in perm:
        q = perm[q]
    return (proc,p,a,q)

def apply_stateperm_var_full(perm, var, proc):
    (proc_pr, p, a, q) = var
    if proc != proc_pr:
        return var
    if p in perm:
        p = perm[p]
    if q in perm:
        q = perm[q]
    return (proc,p,a,q)

def apply_stateperm_vars_full(perm, vars, proc):
    return [apply_stateperm_var_full(perm, var, proc) for var in vars]

def apply_stateperm_asgn(perm, sigma, proc):
    sigma_permed = {}
    for k in sigma:
        (proc_pr,p,a,q) = k
        if proc != proc_pr:
            continue
        v = apply_stateperm_var(perm,(p,a,q), proc)
        sigma_permed[v] = sigma[k]

    return sigma_permed

def mk_eq_class(permable, proc):

    permable = sorted(permable)

    def eq_class(sigma):
        for perm in permutation_dicts(permable):
            sigma_permed = apply_stateperm_asgn(perm, sigma, proc)
            yield sigma_permed

    return eq_class

def rotate(l, n):
    return l[n:] + l[:n]

def ceil_log(n):
    bl = int.bit_length(n)
    if n == 2**(bl-1):
        return bl - 1
    else:
        return bl

def char_cycles(permable):

    K = len(permable)
    for i in range(2,K+1):
        shift = 1
        for exp in range(1, ceil_log(i)+1):
            ys = rotate(permable[:i], shift) + permable[i:]
            yield dict(zip(permable, ys))
            shift *= 2
