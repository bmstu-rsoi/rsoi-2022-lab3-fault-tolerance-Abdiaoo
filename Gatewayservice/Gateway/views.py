import json
from django.shortcuts import render
import requests
from django.core.paginator import Paginator
from django.core import serializers
from rest_framework import viewsets,status
from rest_framework.response import Response
from django.http import JsonResponse
import json
from datetime import datetime
from time import sleep
from django.shortcuts import redirect
import time
usernamesloyaltydown=[]
class GatewayhealthSet(viewsets.ViewSet):
    def getHealth(self,request):
        return JsonResponse({},status=status.HTTP_200_OK)
class GatewayViewSet(viewsets.ViewSet):
    def list_loyalty(self,request):
        username=request.headers['X-User-Name']
        try:
            loyalties_check=requests.get('http://loyaltyservice:8050/manage/health')
        except requests.exceptions.ConnectionError:
            return JsonResponse({'message':'Loyalty Service unavailable'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        loyalties=requests.get('http://loyaltyservice:8050/api/v1/loyalty')
        if loyalties.status_code != 200:
            return JsonResponse(status=status.HTTP_400_BAD_REQUEST)
        for loyalty in loyalties.json():
            if loyalty['username']==username:
                userLoyalty=loyalty
                break
        return JsonResponse(userLoyalty,status=status.HTTP_200_OK,safe=False,json_dumps_params={'ensure_ascii': False})
    def bookaHotel(self,request):
        username=request.headers['X-User-Name']
        try:
            loyalties_check=requests.get('http://loyaltyservice:8050/manage/health')
        except requests.exceptions.ConnectionError:
            return JsonResponse({'message':'Loyalty Service unavailable'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        try:
            reservation_check=requests.get('http://reservationservice:8070/manage/health')
        except requests.exceptions.ConnectionError:
            return JsonResponse({'message':'Reservation Service unavailable'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        hotels=requests.get('http://reservationservice:8070/api/v1/hotels')
        if hotels.status_code!=200:
            return JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        for hotel in hotels.json():
            if hotel['hotelUid']==request.data['hotelUid']:
                choosedHotel=hotel
                break
        loyalties=requests.get('http://loyaltyservice:8050/api/v1/loyalty')
        if loyalties.status_code!=200:
            return JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        for loyalty in loyalties.json():
            if loyalty['username']==username:
                userLoyalty=loyalty
                break
        d1 = datetime.strptime(request.data['endDate'], "%Y-%m-%d")
        d2 = datetime.strptime(request.data['startDate'], "%Y-%m-%d")
        days=d1-d2
        price=hotel['price']*days.days
        cost=price-(price*userLoyalty['discount']/100)
        try:
            payment_check=requests.get('http://paymentservice:8060/manage/health')
        except requests.exceptions.ConnectionError:
            return JsonResponse({'message':'Payment Service unavailable'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        payment=requests.post('http://paymentservice:8060/api/v1/Payment',json={'status':'PAID','price':cost})
        if payment.status_code!=201:
            return JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        numberReservation=userLoyalty['reservationCount']+1
        status_loyalty="BRONZE"
        if(numberReservation>=10):
            status_loyalty="SILVER"
        if(numberReservation>=20):
            status_loyalty="GOLD"
        updateloyalty=requests.patch('http://loyaltyservice:8050/api/v1/loyalty/{}'.format(userLoyalty['id']),data={'status':status_loyalty,'reservationCount':numberReservation})
        if updateloyalty.status_code!=200:
            return JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        data={'username':userLoyalty['username'],'paymentUid':payment.json()['paymentUid'],'hotel_id':choosedHotel['id'],'status':'PAID','startDate':request.data['startDate'],'endDate':request.data['endDate']}
        reservation=requests.post('http://reservationservice:8070/api/v1/reservations',data=data)
        if reservation.status_code!=200:
            return JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        data={'reservationUid':reservation.json()['reservationUid'],'hotelUid':choosedHotel['hotelUid'],'startDate':reservation.json()['startDate'],'endDate':reservation.json()['endDate'],'discount':userLoyalty['discount'],'status':reservation.json()['status'],'payment':payment.json()}
        return JsonResponse(data,status=status.HTTP_200_OK,safe=False,json_dumps_params={'ensure_ascii': False})
    
    def GetInfoUser(self,request):
        loyalty_down=False;
        username=request.headers['X-User-Name']
        try:
            loyalties_check=requests.get('http://loyaltyservice:8050/manage/health')
        except requests.exceptions.ConnectionError:
            loyalty_down=True
        if (loyalty_down):
            userLoyalty={}
        else:
            loyalties=requests.get('http://loyaltyservice:8050/api/v1/loyalty')
            if loyalties.status_code!=200:
                return JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
            for loyalty in loyalties.json():
                if loyalty['username']==username:
                    userLoyalty=loyalty
                    break
        try:
            reservation_check=requests.get('http://reservationservice:8070/manage/health')
        except requests.exceptions.ConnectionError:
            return JsonResponse({'message':'Reservation Service unavailable'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        reservations=requests.get('http://reservationservice:8070/api/v1/reservations')
        if reservations.status_code!=200:
            return JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        userReservations=[reservation for reservation in reservations.json() if reservation['username']==username]
        hotels=requests.get('http://reservationservice:8070/api/v1/hotels')
        if hotels.status_code!=200:
            return JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        try:
            payment_check=requests.get('http://paymentservice:8060/manage/health')
        except requests.exceptions.ConnectionError:
            return JsonResponse({'message':'Payment Service unavailable'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        payments=requests.get('http://paymentservice:8060/api/v1/Payment')
        if payments.status_code!=200:
            return JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        infosUser=[]
        for reservation in userReservations:
            for hotel in hotels.json():
                if hotel['id']==reservation['hotel_id']:
                    reservedHotel=hotel
                    break
            for paymen in payments.json():
                if paymen['paymentUid']==reservation['paymentUid']:
                    payment=paymen
                    break
            reservedHotel['fullAddress']=reservedHotel['country']+', '+reservedHotel['city']+', '+reservedHotel['address']
            data={'reservationUid':reservation['reservationUid'],'hotel':reservedHotel,'startDate':reservation['startDate'],'endDate':reservation['endDate'],'status':reservation['status'],'payment':payment}
            infosUser.append(data)
        return JsonResponse({'reservations':infosUser,"loyalty":userLoyalty},status=status.HTTP_200_OK,safe=False,json_dumps_params={'ensure_ascii': False})
    
    def UserSpecificReservation(self,request,reservationUid=None):
        username=request.headers['X-User-Name']
        try:
            reservation_check=requests.get('http://reservationservice:8070/manage/health')
        except requests.exceptions.ConnectionError:
            return JsonResponse({'message':'Reservation Service unavailable'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        reservation=requests.get('http://reservationservice:8070/api/v1/reservations/{}'.format(reservationUid))
        if reservation.status_code!=200:
            return JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        hotel=requests.get('http://reservationservice:8070/api/v1/hotels/{}'.format(reservation.json()['hotel_id']))
        if hotel.status_code!=200:
            return JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        try:
            payment_check=requests.get('http://paymentservice:8060/manage/health')
        except requests.exceptions.ConnectionError:
            return JsonResponse({'message':'Payment Service unavailable'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        payment=requests.get('http://paymentservice:8060/api/v1/Payment/{}'.format(reservation.json()['paymentUid']))
        if payment.status_code!=200:
            return JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        hoteldict=hotel.json()
        hoteldict['fullAddress']=hotel.json()['country']+', '+hotel.json()['city']+', '+hotel.json()['address']
        if reservation.json()['username']!=username:
            return JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        data={'reservationUid':reservation.json()['reservationUid'],'hotel':hoteldict,'hotelUid':hotel.json()['hotelUid'],'startDate':reservation.json()['startDate'],'endDate':reservation.json()['endDate'],'status':reservation.json()['status'],'payment':payment.json()}
        return JsonResponse(data,status=status.HTTP_200_OK,safe=False,json_dumps_params={'ensure_ascii': False})
    def hotels(self,request):
        try:
            reservation_check=requests.get('http://reservationservice:8070/manage/health')
        except requests.exceptions.ConnectionError:
            return JsonResponse({'message':'Reservation Service unavailable'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        hotels=requests.get('http://reservationservice:8070/api/v1/hotels')
        if hotels.status_code != 200:
            return JsonResponse({'message':'je sais pas'},status=status.HTTP_400_BAD_REQUEST)
        paginator = Paginator(hotels.json(), request.GET.get('size'))
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        return JsonResponse({'items':hotels.json(),"totalElements":len(hotels.json()),"page":request.GET.get('page'),"pageSize":int(request.GET.get('size'))},status=status.HTTP_200_OK,safe=False,json_dumps_params={'ensure_ascii': False})
    
        
    def UserReservations(self,request):
        username=request.headers['X-User-Name']
        try:
            reservation_check=requests.get('http://reservationservice:8070/manage/health')
        except requests.exceptions.ConnectionError:
            return JsonResponse({'message':'Reservation Service unavailable'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        reservations=requests.get('http://reservationservice:8070/api/v1/reservations')
        if reservations.status_code!=200:
            JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        userReservations=[reservation for reservation in reservations.json() if reservation['username']==username]
        infoUserReservations=[]
        hotels=requests.get('http://reservationservice:8070/api/v1/hotels')
        if hotels.status_code!=200:
            JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        try:
            payment_check=requests.get('http://paymentservice:8060/manage/health')
        except requests.exceptions.ConnectionError:
            return JsonResponse({'message':'Payment Service unavailable'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        payments=requests.get('http://paymentservice:8060/api/v1/Payment')
        if payments.status_code!=200:
            JsonResponse({},status=status.HTTP_400_BAD_REQUEST)
        for reservation in userReservations:
            for hotel in hotels.json():
                if hotel['id']==reservation['hotel_id']:
                    reservedHotel=hotel
                    break
            for paymen in payments.json():
                if paymen['paymentUid']==reservation['paymentUid']:
                    payment=paymen
            reservedHotel['fullAddress']=reservedHotel['country']+', '+reservedHotel['city']+', '+reservedHotel['address']
            data={'reservationUid':reservation['reservationUid'],'hotel':reservedHotel,'startDate':reservation['startDate'],'endDate':reservation['endDate'],'status':reservation['status'],'payment':payment}
            infoUserReservations.append(data)
        return JsonResponse(infoUserReservations,status=status.HTTP_200_OK,safe=False,json_dumps_params={'ensure_ascii': False})
    
    def cancelReservation(self,request,reservationUid=None):
        global usernamesloyaltydown
        username=request.headers['X-User-Name']
        try:
            reservation_check=requests.get('http://reservationservice:8070/manage/health')
        except requests.exceptions.ConnectionError:
            return JsonResponse({'message':'Reservation Service unavailable'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        reservation=requests.patch('http://reservationservice:8070/api/v1/reservations/{}'.format(reservationUid),data={'status':'CANCELED'})
        if reservation.status_code!=200:
            Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            payment_check=requests.get('http://paymentservice:8060/manage/health')
        except requests.exceptions.ConnectionError:
            return JsonResponse({'message':'Payment Service unavailable'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if reservation.json()['username']==username:
            payment=requests.patch('http://paymentservice:8060/api/v1/Payment/{}'.format(reservation.json()['paymentUid']),data={'status':'CANCELED'})
            if payment.status_code!=200:
                Response(status=status.HTTP_400_BAD_REQUEST)
            try:
                loyalties_check=requests.get('http://loyaltyservice:8050/manage/health')
                loyalties=requests.get('http://loyaltyservice:8050/api/v1/loyalty')
                if loyalties.status_code!=200:
                    Response(status=status.HTTP_400_BAD_REQUEST)
                for loyalty in loyalties.json():
                    if loyalty['username']==username:
                        userLoyalty=loyalty
                        break
                updateloyalty=requests.get('http://loyaltyservice:8050/api/v1/loyalty/{}'.format(userLoyalty['id']))
                if updateloyalty.status_code!=200:
                    Response(status=status.HTTP_400_BAD_REQUEST)
                return Response(status=status.HTTP_204_NO_CONTENT)
            except requests.exceptions.ConnectionError:
                userunupdated=False
                for user in usernamesloyaltydown:
                    if user['username']==username:
                        user['uncountedReservation']=user['uncountedReservation']+1
                    userunupdated=True
                    break
                if userunupdated==False:
                    usernamesloyaltydown.append({'username': username, 'uncountedReservation': 1})
                return Response(status=status.HTTP_204_NO_CONTENT)
