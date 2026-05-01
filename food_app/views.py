from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import FoodItem, Cart, Order, OrderItem, UserProfile, Category
from .forms import SignUpForm, LoginForm, CheckoutForm
from decimal import Decimal
import json


def index(request):
    """Home page view"""
    categories = Category.objects.all()[:4]
    featured_items = FoodItem.objects.filter(is_available=True)[:8]
    context = {
        'categories': categories,
        'featured_items': featured_items,
    }
    return render(request, 'index.html', context)


def menu(request):
    """Menu page with category filtering"""
    categories = Category.objects.all()
    food_items = FoodItem.objects.filter(is_available=True)

    category_id = request.GET.get('category')
    if category_id:
        food_items = food_items.filter(category_id=category_id)

    context = {
        'categories': categories,
        'food_items': food_items,
        'selected_category': int(category_id) if category_id else None,
    }
    return render(request, 'menu.html', context)


def signup_view(request):
    """User signup view"""
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to FoodieHub!')
            return redirect('index')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SignUpForm()

    return render(request, 'signup.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                next_url = request.GET.get('next', 'index')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('index')


@login_required
@require_POST
def add_to_cart(request, food_id):
    """Add item to cart - Updated for AJAX"""
    try:
        food_item = get_object_or_404(FoodItem, id=food_id, is_available=True)

        # Get or create cart item
        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            food_item=food_item,
            defaults={'quantity': 1}
        )

        if not created:
            cart_item.quantity += 1
            cart_item.save()

        # Get updated cart count
        cart_count = Cart.objects.filter(user=request.user).count()

        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'message': f'{food_item.name} added to cart!',
                'cart_count': cart_count,
                'item_quantity': cart_item.quantity,
                'item_total': float(cart_item.get_total_price())
            })

        # For regular POST requests
        messages.success(request, f'{food_item.name} added to cart!')
        return redirect('menu')

    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Error adding item to cart: {str(e)}'
            }, status=400)
        messages.error(request, 'Error adding item to cart.')
        return redirect('menu')


@login_required
def cart_view(request):
    """Shopping cart view - Fixed Decimal conversion"""
    cart_items = Cart.objects.filter(user=request.user)

    if cart_items:
        total = sum(item.get_total_price() for item in cart_items)
        total = Decimal(str(total))
        delivery_charge = Decimal('40') if total > 0 else Decimal('0')
        tax = total * Decimal('0.05')
        grand_total = total + delivery_charge + tax if total > 0 else Decimal('0')
    else:
        total = Decimal('0')
        delivery_charge = Decimal('0')
        tax = Decimal('0')
        grand_total = Decimal('0')

    context = {
        'cart_items': cart_items,
        'total': total,
        'delivery_charge': delivery_charge,
        'tax': tax,
        'grand_total': grand_total,
    }
    return render(request, 'cart.html', context)


@login_required
@require_POST
def update_cart(request):
    """Update cart item quantity - Fixed Decimal conversion"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        action = data.get('action')

        # Handle refresh action (just return current totals)
        if action == 'refresh':
            cart_items = Cart.objects.filter(user=request.user)
            total = sum(item.get_total_price() for item in cart_items)
            total = Decimal(str(total))
            cart_count = cart_items.count()

            return JsonResponse({
                'success': True,
                'cart_count': cart_count,
                'cart_total': float(total),
                'delivery_charge': 40 if total > 0 else 0,
                'tax': float(total * Decimal('0.05')),
                'grand_total': float(total + Decimal('40') + (total * Decimal('0.05'))) if total > 0 else 0,
            })

        cart_item = get_object_or_404(Cart, id=item_id, user=request.user)

        if action == 'increase':
            cart_item.quantity += 1
            cart_item.save()
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
                cart_item = None
        elif action == 'remove':
            cart_item.delete()
            cart_item = None

        # Get updated cart items and totals
        cart_items = Cart.objects.filter(user=request.user)
        total = sum(item.get_total_price() for item in cart_items)
        total = Decimal(str(total))
        cart_count = cart_items.count()

        response_data = {
            'success': True,
            'cart_count': cart_count,
            'cart_total': float(total),
            'delivery_charge': 40 if total > 0 else 0,
            'tax': float(total * Decimal('0.05')),
            'grand_total': float(total + Decimal('40') + (total * Decimal('0.05'))) if total > 0 else 0,
        }

        if cart_item:
            response_data.update({
                'new_quantity': cart_item.quantity,
                'item_total': float(cart_item.get_total_price()),
                'item_id': cart_item.id
            })

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
@login_required
def checkout_view(request):
    """Checkout process - Fixed Decimal conversion"""
    cart_items = Cart.objects.filter(user=request.user)

    if not cart_items:
        messages.warning(request, 'Your cart is empty!')
        return redirect('menu')

    try:
        user_profile = UserProfile.objects.get(user=request.user)
        initial_data = {
            'delivery_address': user_profile.address,
            'phone_number': user_profile.phone_number,
        }
    except UserProfile.DoesNotExist:
        initial_data = {
            'delivery_address': '',
            'phone_number': '',
        }

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            total = sum(item.get_total_price() for item in cart_items)
            total = Decimal(str(total))
            delivery_charge = Decimal('40')
            tax = total * Decimal('0.05')
            grand_total = total + delivery_charge + tax

            order = Order.objects.create(
                user=request.user,
                total_amount=grand_total,
                delivery_address=form.cleaned_data['delivery_address'],
                phone_number=form.cleaned_data['phone_number'],
                payment_method=form.cleaned_data['payment_method'],
                special_instructions=form.cleaned_data['special_instructions']
            )

            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    food_item=cart_item.food_item,
                    quantity=cart_item.quantity,
                    price=cart_item.food_item.price
                )

            # Send email confirmation
            try:
                order_details = ""
                for item in cart_items:
                    order_details += f"{item.food_item.name} x {item.quantity} - ₹{item.get_total_price()}\n"

                email_body = f"""
                Thank you for your order!

                Order Number: {order.order_number}

                Order Details:
                {order_details}

                Subtotal: ₹{total}
                Delivery Charge: ₹{delivery_charge}
                Tax: ₹{tax:.2f}
                Total Amount: ₹{grand_total:.2f}

                Delivery Address: {order.delivery_address}
                Phone: {order.phone_number}

                Your order will be delivered within 30-40 minutes.

                Thank you for choosing FoodieHub!
                """

                send_mail(
                    f'Order Confirmation - {order.order_number}',
                    email_body,
                    'noreply@foodiehub.com',
                    [request.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Email error: {e}")

            # Clear cart
            cart_items.delete()

            messages.success(request, f'Order placed successfully! Order ID: {order.order_number}')
            return redirect('order_confirmation', order_id=order.id)
    else:
        form = CheckoutForm(initial=initial_data)

    total = sum(item.get_total_price() for item in cart_items)
    total = Decimal(str(total))
    context = {
        'form': form,
        'cart_items': cart_items,
        'total': total,
        'delivery_charge': Decimal('40'),
        'tax': total * Decimal('0.05'),
        'grand_total': total + Decimal('40') + (total * Decimal('0.05')),
    }
    return render(request, 'checkout.html', context)


@login_required
def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_confirmation.html', {'order': order})


@login_required
def my_orders(request):
    """User's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    """Order details view"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_detail.html', {'order': order})


def search_food(request):
    """Search food items"""
    query = request.GET.get('q', '')
    if query:
        food_items = FoodItem.objects.filter(name__icontains=query, is_available=True)
    else:
        food_items = FoodItem.objects.none()

    return render(request, 'search_results.html', {'food_items': food_items, 'query': query})


@login_required
def get_cart_count(request):
    """Get cart count for AJAX"""
    count = Cart.objects.filter(user=request.user).count()
    return JsonResponse({'count': count})


@login_required
@require_POST
def cancel_order(request, order_id):
    """Cancel an order"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        if order.status == 'pending':
            order.status = 'cancelled'
            order.save()
            messages.success(request, 'Order cancelled successfully!')
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'Order cannot be cancelled'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})