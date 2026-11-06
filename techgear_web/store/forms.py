import hashlib
from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify

INPUT_CLASS = "form-input"


class LoginForm(forms.Form):
    username = forms.CharField(
        label="Correo",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Correo",
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Contraseña",
                "autocomplete": "current-password",
            }
        ),
    )


class RegisterForm(forms.Form):
    first_name = forms.CharField(
        label="Nombre",
        min_length=2,
        max_length=60,
        widget=forms.TextInput(
            attrs={"class": "auth-input", "placeholder": "Nombre", "autocomplete": "given-name", "autofocus": True}
        ),
    )
    last_name = forms.CharField(
        label="Apellido",
        min_length=2,
        max_length=60,
        widget=forms.TextInput(
            attrs={"class": "auth-input", "placeholder": "Apellido", "autocomplete": "family-name"}
        ),
    )
    email = forms.EmailField(
        label="Correo",
        widget=forms.EmailInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Correo",
                "autocomplete": "email",
            }
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Contraseña",
                "autocomplete": "new-password",
            }
        ),
    )
    password_confirm = forms.CharField(
        label="Repetir contraseña",
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Repetir contraseña",
                "autocomplete": "new-password",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Las contraseñas no coinciden.")

        first_name = cleaned_data.get("first_name", "").strip()
        last_name = cleaned_data.get("last_name", "").strip()
        if first_name and last_name:
            cleaned_data["full_name"] = f"{first_name} {last_name}"

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
        widget=forms.EmailInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Correo",
                "autocomplete": "email",
                "autofocus": True,
            }
        ),
    )


class OrderForm(forms.Form):
    customer_name = forms.CharField(
        label="Nombre completo",
        max_length=150,
        required=False,
        initial="Cliente TechGear",
        widget=forms.HiddenInput(),
    )
    customer_email = forms.EmailField(
        label="Correo electrónico",
        required=False,
        initial="cliente@techgear.co",
        widget=forms.HiddenInput(),
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


class AdminProductForm(forms.Form):
    name = forms.CharField(label="Nombre", max_length=160)
    category = forms.CharField(label="Categoría", max_length=80)
    price = forms.DecimalField(label="Precio", min_value=0, max_digits=10, decimal_places=2)
    stock = forms.IntegerField(label="Unidades disponibles", min_value=0)
    image_url = forms.CharField(
        label="URL de imagen",
        max_length=2000,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "https://ejemplo.com/imagen.jpg", "inputmode": "url"}),
    )
    image_file = forms.FileField(
        label="Archivo de imagen",
        required=False,
        widget=forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp,image/gif"}),
    )
    description = forms.CharField(label="Descripción", widget=forms.Textarea(attrs={"rows": 3}))

    def clean(self):
        cleaned_data = super().clean()
        image_url = (cleaned_data.get("image_url") or "").strip()
        image_file = cleaned_data.get("image_file")

        if image_url and image_file:
            raise ValidationError("Elige un archivo o pega una URL, no ambas opciones.")
        if not image_url and not image_file:
            self.add_error("image_url", "Sube una imagen o pega una URL pública.")
        elif image_url and not image_url.startswith("/static/"):
            try:
                forms.URLField().clean(image_url)
            except ValidationError:
                self.add_error("image_url", "Pega una URL pública que comience con http:// o https://.")

        if image_file:
            if image_file.size > 5 * 1024 * 1024:
                self.add_error("image_file", "La imagen no puede pesar más de 5 MB.")
            elif image_file.content_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
                self.add_error("image_file", "Usa una imagen JPG, PNG, WebP o GIF.")
        return cleaned_data


class AdminUserForm(forms.Form):
    username = forms.CharField(label="Usuario", max_length=40)
    full_name = forms.CharField(label="Nombre completo", max_length=120)
    email = forms.EmailField(label="Correo electrónico")
    role = forms.ChoiceField(
        label="Rol",
        choices=(("cliente", "Cliente"), ("administrador", "Administrador")),
    )
    password = forms.CharField(
        label="Contraseña",
        min_length=12,
        required=False,
        widget=forms.PasswordInput(render_value=False),
    )

    def __init__(self, *args, require_password=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].required = require_password
