import hashlib

from django import forms
from django.utils.text import slugify

INPUT_CLASS = "form-input"
SELECT_CLASS = "form-select"
TEXTAREA_CLASS = "form-textarea"


class LoginForm(forms.Form):
    username = forms.CharField(
        label="Correo o usuario",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={
                "class": INPUT_CLASS,
                "autocomplete": "current-password",
            }
        ),
    )


class RegisterForm(forms.Form):
    full_name = forms.CharField(
        label="Nombre",
        max_length=120,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "autocomplete": "name"}),
    )
    email = forms.EmailField(
        label="Correo",
        widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Contraseña",
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "autocomplete": "new-password"}),
    )
    password_confirm = forms.CharField(
        label="Confirmar contraseña",
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "autocomplete": "new-password"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Las contraseñas no coinciden.")

        email = cleaned_data.get("email")
        if email:
            local_part = email.rsplit("@", 1)[0]
            username_base = slugify(local_part).replace("-", "")[:30] or "cliente"
            email_suffix = hashlib.sha1(email.lower().encode("utf-8")).hexdigest()[:7]
            cleaned_data["username"] = f"{username_base}_{email_suffix}"[:40]
        return cleaned_data


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label="Correo",
        widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "autocomplete": "email", "autofocus": True}),
    )


class SetPasswordForm(forms.Form):
    password = forms.CharField(
        label="Nueva contraseña",
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "placeholder": "Mínimo 8 caracteres", "autocomplete": "new-password"}),
    )
    password_confirm = forms.CharField(
        label="Confirma tu contraseña",
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "placeholder": "Repite tu contraseña", "autocomplete": "new-password"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("password_confirm"):
            self.add_error("password_confirm", "Las contraseñas no coinciden.")
        return cleaned_data


class ProductForm(forms.Form):
    name = forms.CharField(
        label="Nombre",
        max_length=150,
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASS, "placeholder": "Teclado Mecánico RGB"}
        ),
    )
    description = forms.CharField(
        label="Descripción",
        widget=forms.Textarea(
            attrs={
                "class": TEXTAREA_CLASS,
                "rows": 4,
                "placeholder": "Describe las características del producto...",
            }
        ),
    )
    price = forms.DecimalField(
        label="Precio (USD)",
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": INPUT_CLASS, "step": "0.01", "min": "0"}
        ),
    )
    stock = forms.IntegerField(
        label="Stock",
        min_value=0,
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "min": "0"}),
    )
    category = forms.CharField(
        label="Categoría",
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASS, "placeholder": "Periféricos"}
        ),
    )
    image = forms.URLField(
        label="Imagen (URL)",
        max_length=500,
        widget=forms.URLInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "https://ejemplo.com/imagenes/producto.jpg",
            }
        ),
    )

    def to_api_data(self) -> dict:
        data = self.cleaned_data
        return {
            "name": data["name"],
            "description": data["description"],
            "price": float(data["price"]),
            "stock": data["stock"],
            "category": data["category"],
            "image": data["image"],
        }


class UserForm(forms.Form):
    username = forms.CharField(
        label="Nombre de usuario",
        max_length=150,
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASS, "placeholder": "carlos.rodriguez"}
        ),
    )
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={"class": INPUT_CLASS, "placeholder": "carlos@example.com"}
        ),
    )
    full_name = forms.CharField(
        label="Nombre completo",
        max_length=150,
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASS, "placeholder": "Carlos Rodríguez"}
        ),
    )
    role = forms.ChoiceField(
        label="Rol",
        choices=[
            ("cliente", "Cliente"),
            ("administrador", "Administrador"),
        ],
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    password = forms.CharField(
        label="Contraseña",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "••••••••",
                "autocomplete": "new-password",
            }
        ),
        help_text="Obligatoria al crear un usuario. Déjala vacía para conservarla.",
    )

    def __init__(self, *args, require_password: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.require_password = require_password
        if require_password:
            self.fields["password"].required = True

    def to_api_data(self, require_password: bool | None = None) -> dict:
        data = self.cleaned_data
        payload = {
            "username": data["username"],
            "email": data["email"],
            "full_name": data["full_name"],
            "role": data["role"],
        }
        password_required = self.require_password if require_password is None else require_password
        if data.get("password"):
            payload["password"] = data["password"]
        elif password_required:
            raise ValueError("La contraseña es obligatoria.")
        return payload


class OrderForm(forms.Form):
    customer_name = forms.CharField(
        label="Nombre completo",
        max_length=150,
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASS, "placeholder": "Carlos Rodríguez"}
        ),
    )
    customer_email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={"class": INPUT_CLASS, "placeholder": "carlos@example.com"}
        ),
    )
    quantity = forms.IntegerField(
        label="Cantidad",
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "min": "1",
                "value": "1",
                "inputmode": "numeric",
                "data-order-quantity": "",
            }
        ),
    )


class OrderStatusForm(forms.Form):
    status = forms.ChoiceField(
        label="Estado",
        choices=[
            ("pendiente", "Pendiente"),
            ("en proceso", "En proceso"),
            ("completado", "Completado"),
            ("cancelado", "Cancelado"),
        ],
        widget=forms.Select(attrs={"class": "status-select"}),
    )
