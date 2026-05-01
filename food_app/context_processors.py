from .models import Cart

def cart_count(request):
    """Context processor to add cart count to all templates"""
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()
        return {'cart_count': cart_count}
    return {'cart_count': 0}