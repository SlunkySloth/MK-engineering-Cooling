(function($){
    "use strict";

    $(window).on('load resize', function(){
        HeightResizeWls();
    });

    $(function () {
        HeightResizeWls();
        $('.rt-wpls').each(function(){
            var $carousel = $( this ).find('.rt-row.wpls-carousel');
            if($carousel.length) {
                $.when( $carousel.slick({
                    responsive: [
                        {
                            breakpoint: 600,
                            settings: {
                                slidesToShow: 2,
                                slidesToScroll: 2
                            }
                        },
                        {
                            breakpoint: 480,
                            settings: {
                                slidesToShow: 1,
                                slidesToScroll: 1
                            }
                        }
                    ]
                }) ).done(function() {
                    HeightResizeWls();
                });
            }
        });
    });





    function HeightResizeWls(){
        jQuery(".rt-container-fluid").each(function(){
            var rtMaxH = 0;
            jQuery(this).children('div.rt-row').find(".rt-equal-height").height("auto");
            jQuery(this).children('div.rt-row').find('.rt-equal-height').each(function(){
                var $thisH = jQuery(this).actual( 'outerHeight' );
                if($thisH > rtMaxH){
                    rtMaxH = $thisH;
                }
            });
            jQuery(this).children('div.rt-row').find(".rt-equal-height").css('height', rtMaxH + "px");
        });
    }

})(jQuery);