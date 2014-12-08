// using jQuery
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
var csrftoken = getCookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    crossDomain: false, // obviates need for sameOrigin test
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

function updateTable() {
    $('tbody').load(location.href + ' tbody>tr', function(responseText, textStatus) {
        if ( textStatus == 'success' ) {
            $('#primary-nav').replaceWith($(responseText).find('#primary-nav'));
        }
        $(this)
            .find('.time').time().end()
            .find('.time-age').timeAge().end()
            .find('.time-diff').timeDiff().end()
        ;
    });
}

$.fn.time = function() {
    this.each(function() {
        var time = moment($(this).data('time'));
        $(this).text(time.format('dddd, MMMM, Do YYYY, h:mm:ss a'));
    });
    return this;
};
$.fn.timeAge = function() {
    this.each(function() {
        var time = moment($(this).data('time'));
        $(this).text(time.fromNow());
        $(this).attr('title', time.format('dddd, MMMM, Do YYYY, h:mm:ss a'));
    });
    return this;
};
$.fn.timeDiff = function() {
    this.each(function() {
        var start, end;
        start = moment($(this).data('start'));
        if ($(this).data('end')) {
            // In progress tasks won't have an end set.
            end = moment($(this).data('end'));
        }

        if ( ! end || end == '+0000' ) {
            end = moment();
        }
        if ( end.diff(start, 'seconds') > 300 ) {
            $(this).text(end.from(start, true));
        }
        else {
            $(this).text(end.diff(start, 'seconds') + ' seconds');
        }
    });
    return this;
};

$('.time').time();
$('.time-age').timeAge();
$('.time-diff').timeDiff();

$('a.screenshot').click(function(e) {
    e.preventDefault();

    var big_img = $('<img>')
        .attr('src', $(e.target).attr('src'))
        .click(function(e) { e.stopPropagation(); });
    var container = $('<div class="big-screenshot"><a class="remove btn"><i class="icon-remove"></i></a></div>');
    container.append(big_img);

    var remove_cb = function() {
        container.remove();
        $('.overlay').hide();
    };

    container.find('.remove').on('click', remove_cb);
    $('.overlay').show();
    container.appendTo('body>.container');

    // Set in next event loop so it doesn't apply to the click that ran this
    // code in the first place
    setTimeout(function() {
        $(document).one('click', remove_cb);
    }, 0);
});
