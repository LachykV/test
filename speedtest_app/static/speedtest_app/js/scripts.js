function setProgress(elementId, value, maxValue) {
    const percentage = Math.min((value / maxValue) * 100, 100);
    $(`#${elementId}`).css({
        'width': `${percentage}%`,
        'transition': 'width 0.5s ease-in-out'
    });
}

$(document).ready(function() {
    $('#check-speed').click(function() {
        const button = $(this);
        const buttonText = $('#button-text');

        button.prop('disabled', true);
        buttonText.html('<span class="loading-animation"></span>Testing you internet speed...');

        $('.progress-bar').css({
            'width': '0%',
            'transition': 'none'
        });

        $('#download-speed').text('-- Mbps');
        $('#upload-speed').text('-- Mbps');
        $('#ping-value').text('-- ms');

        $.ajax({
            url: speedTestUrl,
            method: 'GET',
            success: function(response) {
                if (response.success) {
                    $('#download-speed').text(`${response.download_speed} Mbps`);
                    $('#upload-speed').text(`${response.upload_speed} Mbps`);
                    $('#ping-value').text(`${response.ping} ms`);

                    setProgress('download-progress', response.download_speed, 100);
                    setProgress('upload-progress', response.upload_speed, 100);
                    setProgress('ping-progress', response.ping, 100);
                    $('#is-fast-text').text(response.is_fast ? 'Так' : 'Ні');
                    $('#summary-text').text(response.summary);
                    $('#internet-quality').removeClass('hidden');
                } else {
                    alert('Error performing speed test: ' + response.error);
                }
            },
            error: function() {
                alert('Error connecting to server');
            },
            complete: function() {
                button.prop('disabled', false);
                buttonText.html('Start Speed Test');
            }
        });
    });
});
