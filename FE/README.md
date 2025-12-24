# iPoor
MIS for Poverty Reduction 

## Frontend quickstart
- Static HTML lives in `FE/FE/` (Auth, HomePage, LandingPage).
- Backend API base defaults to `http://127.0.0.1:8000` in inline scripts. Update `API_BASE_URL` in `FE/FE/Auth/Login.html`, `Signup.html`, and `HomePage.html` if running backend elsewhere.
- Login calls `POST /auth/login` and stores JWT in `ipoor_access_token` (localStorage if “remember me” checked, otherwise sessionStorage).
- Signup calls `POST /auth/register`, then auto-login and redirects to Login.
- Dashboard fetches latest households from `GET /households?limit=5`; requires JWT. If missing/expired token, user is redirected to Login.
