from django import forms

INPUT_CLASS = "form-input"
SELECT_CLASS = "form-select"
TEXTAREA_CLASS = "form-textarea"


class LoginForm(forms.Form):
    username = forms.CharField(
        label="Usuario o correo electrónico",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "admin@techgear.com",
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
                "placeholder": "••••••••",
                "autocomplete": "current-password",
            }
        ),
    )


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
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "min": "1", "value": "1"}),
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
