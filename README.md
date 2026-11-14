# 🏡 StayNest – Airbnb Clone

A full-stack accommodation booking platform inspired by Airbnb, built using **Python, Django REST Framework, React.js, and PostgreSQL**.

StayNest allows users to discover properties, explore accommodation details, book stays, manage reservations, and list their own properties as hosts.

## 🚀 Project Overview

StayNest is a full-stack web application designed to simplify the property rental and booking experience. It provides separate functionalities for guests, hosts, and administrators.

The project focuses on building a scalable backend architecture, secure REST APIs, real-time availability validation, and a responsive frontend.

## 🛠️ Tech Stack

### Backend
- Python
- Django
- Django REST Framework
- PostgreSQL
- JWT Authentication
- Django ORM
- Redis (planned)
- Cloudinary (planned)

### Frontend
- React.js
- Vite
- JavaScript
- Tailwind CSS
- React Router DOM
- Axios
- Context API / Redux Toolkit

### Tools
- Git & GitHub
- Postman
- VS Code
- Docker (planned)

## ✨ Features

### 👤 Authentication & User Management
- User registration and login.
- JWT-based authentication.
- Access and refresh token management.
- User profile management.
- Role-based permissions.
- Guest, Host, and Admin roles.

### 🏠 Property Management
- Create, update, and delete property listings.
- Upload multiple property images.
- Add property descriptions and locations.
- Set nightly prices.
- Manage amenities and property details.
- Set maximum guest capacity.

### 🔍 Property Search
- Search properties by location.
- Filter by price range.
- Filter by property type.
- Filter by amenities.
- Search based on check-in and check-out dates.
- Guest-based filtering.

### 📅 Booking Management
- Book available properties.
- Check property availability.
- Calculate total booking price.
- View booking history.
- Cancel reservations.
- Prevent overlapping bookings.
- Host booking management.

### 💳 Payment Management
- Payment gateway integration (planned).
- Payment verification.
- Transaction history.
- Payment status management.

### ⭐ Reviews & Ratings
- Submit property reviews.
- Rate properties.
- Display average ratings.
- View customer feedback.

### ❤️ Wishlist
- Save favorite properties.
- Remove properties from wishlist.
- View saved accommodations.

### 📊 Dashboards
- Host dashboard.
- Property management.
- Booking statistics.
- Earnings overview.
- Admin management dashboard.

## 📁 Project Structure

```text
StayNest/
│
├── backend/
│   ├── config/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── properties/
│   │   ├── bookings/
│   │   ├── payments/
│   │   ├── reviews/
│   │   ├── wishlist/
│   │   └── dashboard/
│   │
│   ├── media/
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── layouts/
│   │   ├── hooks/
│   │   ├── context/
│   │   ├── routes/
│   │   └── utils/
│   │
│   └── package.json
│
└── README.md
```

## ⚙️ Installation & Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-username/StayNest.git

cd StayNest
```

### 2. Backend Setup

```bash
cd backend

python -m venv venv
```

Activate virtual environment:

**Windows:**
```bash
venv\Scripts\activate
```

**Linux / macOS:**
```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure your `.env` file using `.env.example`.

Run database migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

Create superuser:

```bash
python manage.py createsuperuser
```

Start Django server:

```bash
python manage.py runserver
```

Backend URL:

```text
http://127.0.0.1:8000/
```

### 3. Frontend Setup

Open another terminal:

```bash
cd frontend

npm install
```

Start React development server:

```bash
npm run dev
```

Frontend URL:

```text
http://localhost:5173/
```

## 🔐 Environment Variables

Create a `.env` file inside the backend directory.

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_NAME=StayNest
DATABASE_USER=postgres
DATABASE_PASSWORD=your-password
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

Never commit your actual `.env` file to GitHub.

## 🔗 API Endpoints

| Module | Endpoint | Method |
|---|---|---|
| Register | `/api/auth/register/` | POST |
| Login | `/api/auth/login/` | POST |
| Profile | `/api/auth/profile/` | GET |
| Properties | `/api/properties/` | GET |
| Create Property | `/api/properties/` | POST |
| Property Details | `/api/properties/{id}/` | GET |
| Create Booking | `/api/bookings/` | POST |
| My Bookings | `/api/bookings/` | GET |
| Reviews | `/api/reviews/` | POST |
| Wishlist | `/api/wishlist/` | GET |

*Endpoints will be updated as development progresses.*

## 🧪 Testing

Backend APIs can be tested using Postman.

Testing includes:
- Authentication and authorization.
- Property CRUD operations.
- Booking availability.
- Booking date conflicts.
- User role permissions.
- Payment verification.
- API validation and error handling.

## 🗺️ Development Roadmap

- [x] Project concept and technology stack selection.
- [ ] Django project setup.
- [ ] PostgreSQL database integration.
- [ ] Database models and relationships.
- [ ] JWT authentication.
- [ ] Property management APIs.
- [ ] Search and filtering.
- [ ] Booking and availability system.
- [ ] Payment integration.
- [ ] Reviews and ratings.
- [ ] Wishlist functionality.
- [ ] Host dashboard.
- [ ] Admin dashboard.
- [ ] React frontend.
- [ ] API integration.
- [ ] Testing and deployment.

## 🔮 Future Improvements

- Real-time notifications.
- Redis caching.
- Celery background tasks.
- Google Maps integration.
- Email notifications.
- Advanced search and recommendations.
- Docker-based deployment.
- CI/CD pipeline.

## 🎯 Project Goals

This project aims to demonstrate practical full-stack development skills, including:

- REST API development using Django REST Framework.
- Database design using PostgreSQL.
- JWT authentication and role-based authorization.
- Complex booking and availability logic.
- React frontend development.
- Backend optimization and scalable architecture.

## 👨‍💻 Author

**Your Name**

Full Stack Developer | Python | Django | React | PostgreSQL


---

⭐ If you find this project interesting, consider giving it a star!

*This project is developed for educational and portfolio purposes. It is not affiliated with Airbnb.*
