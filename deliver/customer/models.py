from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser, UserManager as DefaultUserManager
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class CustomUserManager(DefaultUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(username, email, password, **extra_fields)


class CustomUser(AbstractUser):
    email = models.EmailField(_('email address'), unique=True, blank=False, null=False)

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Custom User'
        verbose_name_plural = 'Custom Users'
        db_table = 'custom_user'


class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='menu_images/')
    price = models.DecimalField(max_digits=5, decimal_places=2)
    category = models.ManyToManyField('Category', related_name='item')
    max_quantity = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return self.name
    
class Category(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name
    
class OrderModel(models.Model):
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    
    time_validator = RegexValidator(
        regex=r'^\d{2}:\d{2}$',
        message='Time format must be HH:MM (e.g., 16:24)'
    )
    
    # Using TimeField instead of CharField for time
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    
    # Payment Choices
    METHOD_OF_PAYMENT = (
        ('Cash','Cash'),
        ('Zelle','Zelle'),
        ('Cashapp','Cashapp'),
        ('Venmo','Venmo'),
        ('PayPal','PayPal'),
    )
    TYPE_OF_PAYMENT = (
        ('Advance Payment Deposit','Advance Payment Deposit'),
        ('Full Amount','Full Amount'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    created_on = models.DateTimeField(auto_now_add=True)
    
    # Other fields
    payment_account = models.CharField(max_length=100, blank=True, null=True)
    client_full_name = models.CharField(max_length=75, blank=True, null=True)
    
    # Address fields split
    street_address = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=75, blank=True, null=True)
    state = models.CharField(max_length=2, blank=True, null=True)
    zip_code = models.CharField(max_length=5, blank=True, null=True)
    
    # Telephone and cell number with regex validator
    cell_number = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True)
    
    # Additional fields
    email = models.EmailField(blank=True, null=True)
    date_of_event = models.DateField(blank=True, null=True)
    event_type = models.CharField(max_length=50, blank=True, null=True)
    number_of_guests = models.CharField(max_length=3, blank=True, null=True)
    location_of_event = models.CharField(max_length=50, blank=True, null=True)
    
    # Fields with default values
    type_of_payment = models.CharField(max_length=50, choices=TYPE_OF_PAYMENT, default="Advance Payment Deposit")
    method_of_payment = models.CharField(max_length=50, choices=METHOD_OF_PAYMENT, default="Cash")
    
    # Boolean fields
    is_paid = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    
    # Items and Total Price
    items = models.ManyToManyField('MenuItem', related_name='order', blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def update_total_price(self):
        self.total_price = self.calculate_total_price()
        self.save()
    
    def __str__(self):
        return f'Order: {self.created_on.strftime("%b %d %I: %M %p")} - Customer: { self.client_full_name }'
    
    def calculate_total_price(self):
        total = 0
        for item in self.items.all():
            total += item.price
        return total
    
    def save(self, *args, **kwargs):
        # if not self.items.exists():
        #     raise ValidationError("An order must have at least one item.")
        super(OrderModel, self).save(*args, **kwargs)


 
# Cart Item Model
class CartItem(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    order = models.ForeignKey(OrderModel, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.IntegerField(null=True,blank=True, default=1)


    def __str__(self):
        return f"{self.menu_item.name} (x{self.quantity})"