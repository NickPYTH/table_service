from tables.models import TablePermission, TableFilialPermission, Profile


def get_table_ids_permissions(user):
    permissions_user = set(TablePermission.objects.filter(user=user).values_list('table__id', flat=True))
    filial_id = (Profile.objects
                 .filter(user=user)
                 .select_related('employee')
                 .values_list('employee__id_filial', flat=True)
                 .first())
    permissions_filial = set(
        TableFilialPermission.objects.filter(filial__id=filial_id).values_list('table__id', flat=True))
    all_permissions = permissions_user | permissions_filial
    return all_permissions