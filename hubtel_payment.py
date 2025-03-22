import os
import requests
import json
from flask import Blueprint, request, jsonify, current_app
from config import Config

# Create a Blueprint for Hubtel payment routes
hubtel_bp = Blueprint('hubtel', __name__)

# Get Hubtel API credentials from Config
def get_hubtel_credentials():
    return {
        'merchant_account': Config.HUBTEL_MERCHANT_ACCOUNT,
        'api_key': Config.HUBTEL_API_ID,
        'client_secret': Config.HUBTEL_API_KEY
    }

@hubtel_bp.route('/initiate-hubtel-payment', methods=['POST'])
def initiate_hubtel_payment():
    """Initiate a Hubtel payment transaction"""
    credentials = get_hubtel_credentials()
    
    if not credentials['merchant_account'] or not credentials['api_key'] or not credentials['client_secret']:
        current_app.logger.error("Missing Hubtel API credentials")
        return jsonify({
            'responseCode': '4001', 
            'status': 'Failed',
            'message': 'Configuration error. Please contact support.'
        }), 500
    
    # Get request data
    data = request.json
    
    # Set merchant account number from environment variable
    data['merchantAccountNumber'] = credentials['merchant_account']
    
    try:
        # Make request to Hubtel API
        response = requests.post(
            "https://payproxyapi.hubtel.com/items/initiate",
            json=data,
            auth=(credentials['api_key'], credentials['client_secret'])
        )
        
        # Log the response for debugging
        current_app.logger.info(f"Hubtel API response: {response.text}")
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            current_app.logger.error(f"Hubtel API error: {response.status_code}, {response.text}")
            return jsonify({
                'responseCode': str(response.status_code),
                'status': 'Failed',
                'message': 'Payment initiation failed.'
            }), response.status_code
            
    except Exception as e:
        current_app.logger.error(f"Exception in Hubtel payment: {str(e)}")
        return jsonify({
            'responseCode': '5000',
            'status': 'Error',
            'message': 'An unexpected error occurred.'
        }), 500

@hubtel_bp.route('/hubtel-callback', methods=['POST'])
def hubtel_callback():
    """Handle Hubtel payment callbacks"""
    try:
        data = request.json
        
        # Log the callback data
        current_app.logger.info(f"Hubtel Callback received: {json.dumps(data)}")
        
        if data.get('ResponseCode') == '0000' and data.get('Data', {}).get('Status') == 'Success':
            client_reference = data.get('Data', {}).get('ClientReference')
            
            # Update order payment status using the client_reference which is our order_number
            from routes import update_payment_method
            update_payment_method(client_reference, 'paid')
            current_app.logger.info(f"Payment successful for order: {client_reference}")
            
        return jsonify({'status': 'success'})
            
    except Exception as e:
        current_app.logger.error(f"Error in Hubtel callback: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@hubtel_bp.route('/check-payment-status', methods=['GET'])
def check_payment_status():
    """Check the status of a Hubtel payment"""
    credentials = get_hubtel_credentials()
    client_reference = request.args.get('clientReference')
    
    if not client_reference:
        return jsonify({'error': 'Missing clientReference parameter'}), 400
    
    try:
        # Make request to Hubtel API to check transaction status
        response = requests.get(
            f"https://api-txnstatus.hubtel.com/transactions/{credentials['merchant_account']}/status",
            params={'clientReference': client_reference},
            auth=(credentials['api_key'], credentials['client_secret'])
        )
        
        # Log the response for debugging
        current_app.logger.info(f"Hubtel status check response: {response.text}")
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            current_app.logger.error(f"Hubtel status check error: {response.status_code}, {response.text}")
            return jsonify({
                'responseCode': str(response.status_code),
                'status': 'Failed',
                'message': 'Failed to check payment status.'
            }), response.status_code
            
    except Exception as e:
        current_app.logger.error(f"Exception in check payment status: {str(e)}")
        return jsonify({
            'responseCode': '5000',
            'status': 'Error',
            'message': 'An unexpected error occurred.'
        }), 500

# Additional routes for order completion and cancellation
@hubtel_bp.route('/order-complete')
def order_complete():
    """Handle order completion after successful payment"""
    client_reference = request.args.get('clientReference')
    
    try:
        # Check payment status from Hubtel
        credentials = get_hubtel_credentials()
        response = requests.get(
            f"https://api-txnstatus.hubtel.com/transactions/{credentials['merchant_account']}/status",
            params={'clientReference': client_reference},
            auth=(credentials['api_key'], credentials['client_secret'])
        )
        
        if response.status_code == 200:
            payment_data = response.json()
            if payment_data.get('data', {}).get('status') == "Paid":
                # Get total amount from payment data
                amount = payment_data.get('data', {}).get('amount', 0)
                
                # Redirect to order confirmation with order number and total
                from flask import redirect, url_for
                return redirect(url_for('app.order_confirmation', 
                                       order_number=client_reference,
                                       total=amount))
    
    except Exception as e:
        current_app.logger.error(f"Error in order completion: {str(e)}")
    
    # If anything fails, redirect to the main page
    from flask import redirect, url_for
    return redirect(url_for('app.index'))

@hubtel_bp.route('/order-cancelled')
def order_cancelled():
    """Handle order cancellation"""
    return jsonify({'status': 'cancelled', 'message': 'Payment was cancelled'})
