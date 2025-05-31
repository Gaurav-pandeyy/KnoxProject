# 🛡️ KnoxProject - Social Media Backend API


A robust Django REST Framework (DRF) based backend API for a social media platform, featuring **Knox** token-based authentication. This project provides essential social media functionality with secure authentication, scalable architecture, and modern API design.

---
## 📸 Project Screenshots

### Screenshot 1
![Screenshot 1](https://drive.google.com/uc?export=view&id=1F_8PKbehN3mcjjR8hmQB88inwueRTUvi)

### Screenshot 2
![Screenshot 2](https://drive.google.com/uc?export=view&id=1O2Q6_MiyCjlhAPcAR_HnM71ynGBk1tTi)

### Screenshot 3
![Screenshot 3](https://drive.google.com/uc?export=view&id=1LT7ugQqSs1OlS--Ia-4BQh5qiPPfDBni)

### Screenshot 4
![Screenshot 4](https://drive.google.com/uc?export=view&id=1a-epMhFIfw0zBw8ItU_Il9mrHqdihQQ6)

### Screenshot 5
![Screenshot 5](https://drive.google.com/uc?export=view&id=1PC03SmdceaBrPFCNRVDsglmWD2jm6xtm)

### Screenshot 6
![Screenshot 6](https://drive.google.com/uc?export=view&id=1BVuaqQ_4STLbtvX4ktAeky-YlfxJBi4j)
## 🌟 Key Features

- 🔐 **Secure Authentication** - Knox token-based authentication system
- 🚀 **RESTful API** - Built with Django REST Framework
- 🏗️ **Modular Architecture** - Scalable and maintainable codebase
- 📱 **Social Media Ready** - Core features for social platforms
- 🛡️ **Token Management** - Secure login/logout with token expiry
- 📊 **SQLite Database** - Ready for development and testing

---

## 📁 Project Structure

```
KnoxProject/
├── 📄 manage.py                 # Django management script
├── 🗃️ db.sqlite3               # SQLite database
├── 📁 EFA/                     # Main project configuration
│   ├── ⚙️ settings.py          # Django settings
│   └── 🔗 urls.py              # Main URL configuration
└── 📁 Backend/                 # Core application
    ├── 🏗️ models.py            # Database models
    ├── 👁️ views.py             # API views
    ├── 📋 serializers.py       # Data serializers
    └── 🔗 urls.py              # Backend URL patterns
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip (Python package installer)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd KnoxProject
   ```

2. **Create and activate virtual environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate (Linux/macOS)
   source venv/bin/activate
   
   # Activate (Windows)
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start development server**
   ```bash
   python manage.py runserver
   ```

Your API will be available at `http://127.0.0.1:8000/`

---

## 🔐 Authentication with Knox

Knox provides secure, token-based authentication with automatic token expiry and refresh capabilities.

### Available Endpoints

| Method | Endpoint | Description | Authentication Required |
|--------|----------|-------------|------------------------|
| `POST` | `/register/` | User registration | ❌ |
| `POST` | `/login/` | User login | ❌ |
| `POST` | `/logout/` | User logout | ✅ |

### 📝 API Usage Examples

#### User Registration
```http
POST /register/
Content-Type: application/json

{
  "username": "newuser",
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "user": {
    "id": 1,
    "username": "newuser",
    "email": "user@example.com"
  },
  "token": "your-authentication-token",
  "expiry": "2025-06-01T12:00:00Z"
}
```

#### User Login
```http
POST /login/
Content-Type: application/json

{
  "username": "testuser",
  "password": "yourpassword"
}
```

**Response:**
```json
{
  "expiry": "2025-06-01T12:00:00Z",
  "token": "your-generated-token"
}
```

#### Using Authentication Token
Include the token in your request headers:

```http
Authorization: Token your-generated-token
```

#### User Logout
```http
POST /logout/
Authorization: Token your-generated-token
```

---

## 🛠️ Development

### Running Tests
```bash
python manage.py test
```

### Database Management
```bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Access Django shell
python manage.py shell
```

### Admin Interface
Access the Django admin at `http://127.0.0.1:8000/admin/` with your superuser credentials.

---

## 📚 Dependencies

- **Django** - Web framework
- **Django REST Framework** - API framework
- **django-rest-knox** - Token authentication
- **django-cors-headers** - CORS handling (if needed)

Create a `requirements.txt` file with:
```
Django>=4.0,<5.0
djangorestframework>=3.14.0
django-rest-knox>=4.2.0
django-cors-headers>=3.13.0
```

---

## 🔧 Configuration

### Settings Overview
Key settings in `EFA/settings.py`:

```python
# Knox Configuration
REST_KNOX = {
    'TOKEN_TTL': timedelta(hours=10),
    'AUTO_REFRESH': True,
    'MIN_REFRESH_INTERVAL': 60
}

# DRF Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'knox.auth.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

