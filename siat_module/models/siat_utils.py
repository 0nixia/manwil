def get_siat_employee_config(env):
    """
    Devuelve (employee, pos_rec, pos_code, sucursal_code, user_login)
    para el usuario autenticado en la empresa activa.
    Fallback: si no hay empleado, lee desde res.users (compatibilidad).
    """
    user = env.user
    company = env.company

    employee = env['hr.employee'].search([
        ('user_id', '=', user.id),
        ('company_id', '=', company.id),
    ], limit=1)

    if employee:
        config = employee.siat_pos_ids.filtered(
            lambda r: r.company_id == company
        )[:1]
        pos_rec = config.puntoventa_id
        login   = employee.name or user.login
    else:
        pos_rec = user.puntoventa_id
        login   = user.login

    pos_code     = pos_rec.pos_siat_id     if pos_rec else 0
    sucursal_code = pos_rec.codigo_sucursal if pos_rec else 0
    return employee, pos_rec, pos_code, sucursal_code, login