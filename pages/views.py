from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse

import http.client
import json, asyncio
import requests, concurrent.futures

from pages.models import History


# Establishing the connection to the RapidAPI host
conn = http.client.HTTPSConnection("social-download-all-in-one.p.rapidapi.com")


# HOME PAGE
def home(request):
    # check if user want to download video
    if request.method == "POST":
        video_url = request.POST.get('video_url')
        video_info = PaidAPI_Downloander(video_url)
        # print(video_info)

        if video_info == None or video_info.get('error'):
            if video_info == None:error_msg = "Servers busy. Try again later"
            else:error_msg = video_info.get('message', 'Servers busy. Try again later')

            return JsonResponse({
                "error": True, 
                "message": error_msg
            })
        
        medias = video_info.get('medias')
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            videos = sorted(ex.map(get_info, [m for m in medias if m['type'] == 'video']), key=lambda x: x['size_mb'], reverse=True)
            audios = sorted(ex.map(get_info, [m for m in medias if m['type'] == 'audio']), key=lambda x: x['size_mb'], reverse=True)
        
        video_data = {
            'title': video_info.get('title', ''),
            'thumbnail_url': video_info.get('thumbnail', ''),
            'video_formats': videos,
            'audio_formats': audios
        }

        # Create a new history record
        History.objects.create(
            user_id=request.user.id if request.user.is_authenticated else 0, # ID 0 for guests
            url=video_url,
            data=video_data
        )

        return JsonResponse(video_data)


    return render(request, 'home.html')


# SIGN UP LOGIC
def signup_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        password2 = request.POST['password2']
        
        if password != password2:
            messages.error(request, "Passwords do not match")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
        else:
            user = User.objects.create_user(username=username, password=password)
            user.save()

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                messages.success(request, "Account created! You can login now.")
                return redirect('login')
            
    return render(request, 'signup.html')


# LOGIN LOGIC
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Username or password is incorrect")
    return render(request, 'login.html')


# LOGOUT
def logout_view(request):
    logout(request)
    return redirect('home')


# USER PROFILE
@login_required(login_url='/')
def user_profile(request):
    user = request.user  # Get the logged-in user
    histories = History.objects.filter(user_id=user.id)
    return render(request, 'user_profile.html', {'user': user, 'user_history': histories})


# GET VIDEOS DATA API
def PaidAPI_Downloander(url):

    API_KEY = ""

    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': "social-download-all-in-one.p.rapidapi.com",
        'Content-Type': "application/json"
    }

    payload = json.dumps({
        "url": url
    })

    # Sending the POST request
    full_data, counter = None, 0

    while counter < 2:
        try:
            conn.request("POST", "/v1/social/autolink", payload, headers)
            res = conn.getresponse()
            data = res.read()

            full_data = json.loads(data.decode("utf-8"))
            break
        except Exception as error:pass
        counter += 1
        asyncio.run(asyncio.sleep(1))

    return full_data


# GET FILE SIZE
def get_info(m):
    session = requests.Session()
    size = round(int(session.head(m['url'], allow_redirects=True).headers.get('Content-Length', 0)) / (1024*1024), 2)
    
    return {'url': m['url'], 'quality': m['quality'], 'size_mb': size}
