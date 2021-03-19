from io import BytesIO
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from orders.models import Order

import braintree
import weasyprint


def payment_process(request):
    order_id = request.session.get('order_id')
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        # Токен транзакции
        nonce = request.POST.get('payment_method_nonce', None)
        # Создание транзакции
        result = braintree.Transaction.sale({
            # 'amount': '2000.00', fail Transaction
            'amount': '{:.2f}'.format(order.get_total_cost()),
            'payment_method_nonce': nonce,
            'options': {
                'submit_for_settlement': True
            }
        })
        if result.is_success:
            # Отмечаем оплату и номер транзакции
            order.paid = True
            order.braintree_id = result.transaction.id
            order.save()
            # Создание электронного сообщения.
            subject = 'My Shop - Invoice no. {}'.format(order.id)
            message = 'Please, find attached the invoice for your recent purchase.'
            email = EmailMessage(subject,
                                 message,
                                 'admin@myshop.com',
                                 [order.email])
            # Формирование PDF.
            html = render_to_string('orders/order/pdf.html', {'order': order})
            out = BytesIO()
            stylesheets = [weasyprint.CSS(settings.STATIC_ROOT + 'css/pdf.css')]
            weasyprint.HTML(string=html).write_pdf(out, stylesheets=stylesheets)
            # Прикрепляем PDF к электронному сообщению.
            email.attach('order_{}.pdf'.format(order.id),
                         out.getvalue(),
                         'application/pdf')
            # Отправка сообщения.
            email.send()
            return redirect('payment:done')
        else:
            return redirect('payment:canceled')
    else:
        # Создание токена для JS SDK для формирования формы
        client_token = braintree.ClientToken.generate()
        return render(request,
                      'payment/process.html',
                      {'order': order,
                       'client_token': client_token})


def payment_done(request):
    return render(request, 'payment/done.html')


def payment_canceled(request):
    return render(request, 'payment/canceled.html')
