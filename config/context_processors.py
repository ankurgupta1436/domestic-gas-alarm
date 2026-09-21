from datetime import date


def site_context(request):
    return {"current_year": date.today().year}
