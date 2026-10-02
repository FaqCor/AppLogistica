def obtener_ultimo_km(patente):
    try:
        # Intentamos buscar en los cierres o registros anteriores
        ws_cierres = sheet.worksheet("Cierres")
        registros = ws_cierres.get_all_records()
        kms_vehiculo = []
        for row in registros:
            row_lower = {str(k).strip().lower(): v for k, v in row.items()}
            pat = str(row_lower.get("patente", row_lower.get("dominio", ""))).strip()
            if pat.lower() == patente.strip().lower():
                km_val = row_lower.get("km actual", row_lower.get("kilometraje", 0))
                if str(km_val).replace('.', '', 1).isdigit():
                    kms_vehiculo.append(float(km_val))
        if kms_vehiculo:
            return int(kms_vehiculo[-1])
    except:
        pass

    try:
        # Si no hay en cierres, buscamos en el historial de checklists
        ws_check = sheet.worksheet("Checklist")
        registros = ws_check.get_all_records()
        kms_vehiculo = []
        for row in registros:
            row_lower = {str(k).strip().lower(): v for k, v in row.items()}
            pat = str(row_lower.get("patente", row_lower.get("dominio", ""))).strip()
            if pat.lower() == patente.strip().lower():
                km_val = row_lower.get("km", row_lower.get("kilometraje", 0))
                if str(km_val).replace('.', '', 1).isdigit():
                    kms_vehiculo.append(float(km_val))
        if kms_vehiculo:
            return int(kms_vehiculo[-1])
    except:
        pass
        
    return 0  # Valor por defecto si no hay registros previos
