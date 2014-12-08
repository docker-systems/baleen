jQuery(function() {
    "use strict";

    var $ = jQuery;

    if (typeof(action_data) === 'undefined') {
        return;
    }

    var Action = Backbone.Model.extend({
        idAttribute: 'id',
        defaults: {
            index: null,
            name: '',
            username: '',
            host: '',
            command: '',
            authorized_keys_entry: '',
            hook_success: '',
            hook_failure: '',
            hook_finished: '',
            output_UX: '',
            output_CX: '',
            output_CH: ''
        }
    });

    var ActionSet = Backbone.Collection.extend({
        model: Action,
        url: window.location + '/action',
        comparator: function(model) {
            return model.get('index');
        },
        initialize: function() {
            this.on('add', this.add_it, this);
        },
        add_it: function(m) {
            if (m.get('index') == null) {
                m.set('index', this.length - 1);
            }
        },
    });

    var ActionView = Backbone.View.extend({
        tagName: 'div',
        className: 'deployment-action',
        view_template: _.template($('#action-view-tpl').html()),
        edit_template: _.template($('#action-edit-tpl').html()),
        error_template: _.template($('#error-tpl').html()),
        events: {
            'click a.edit': 'edit',
            'click a.delete': 'delete',
            'click a.save': 'edit_save',
            'click a.cancel': 'edit_cancel',
            'drop': 'drop'
        },
        render: function(e) {
            var data = this.model.toJSON();
            if (this.state == 'view') {
                data.id = this.model.id;
                this.$el.html(this.view_template(data));
            }
            else if (this.state == 'edit') {
                data.id = this.model.id;
                this.$el.html(this.edit_template(data));
            }
            else if (this.state == 'new') {
                data.id = 'new';
                var html = $(this.edit_template(data));
                $('.btn.save', html).html('Add');
                this.$el.html(html);
            }
            this.delegateEvents();
            return this;
        },
        initialize: function() {
            this.state = 'view';
            if ( ! this.model.id ) {
                this.state = 'new';
            }
            this.model.on('change', this.render, this);
        },
        edit: function(e) {
           e.preventDefault();
           this.state = 'edit';
           this.render();
        },
        'delete': function(e) {
           console.log('deleting view event');
           e.preventDefault();
           this.model.destroy();
           this.remove();
        },
        edit_save: function(e) {
            e.preventDefault();
            var form = this.$('form');
            var data = {
                'name': $('input[name="name"]', form).val(),
                'username': $('input[name="username"]', form).val(),
                'host': $('input[name="host"]', form).val(),
                'command': $('textarea[name="command"]', form).val(),
                'output_UX': $('input[name="output_UX"]', form).val(),
                'output_CX': $('input[name="output_CX"]', form).val(),
                'output_CH': $('input[name="output_CH"]', form).val(),
                'hook_failure': $('input[name="hook_failure"]', form).val(),
                'hook_success': $('input[name="hook_success"]', form).val(),
                'hook_finished': $('input[name="hook_finished"]', form).val()
            };
            var this_view = this;

            this.model.save(data, {
                success: function(model, response, options) {
                        if (response['form_saved'] == true) {
                            model.set(response['data']);
                            this_view.state = 'view';
                            this_view.render();
                        } else {
                            var msg = _.reduce(response['errors'], function(memo, value, key) {
                                return memo + '<li>' + key + ':' + value + '</li>';
                            }, '');
                            msg = '<ul>' + msg + '</ul>';
                            this_view.$el.find('div.messages').html(this_view.error_template({msg: msg}));
                        }
                    }
                });
        },
        edit_cancel: function(e) {
            e.preventDefault();
            if ( this.model.id ) {
                this.state = 'view';
                this.render();
            }
            else {
                console.log('deleting view for add');
                this.model.destroy();
                this.remove();
            }
        },
        drop: function(e, index) {
            this.$el.trigger('update-sort', [this.model, index]);
        }
    });

    var ActionSetView = Backbone.View.extend({
        events: {
            'update-sort': 'update_sort',
        },
        initialize: function() {
            // view cache for future reuse and maintaining view state
            this._my_element_views = [];

            this.collection.each(this.add, this);

            this.collection.bind('add', this.add, this);
            this.collection.bind('remove', this.remove, this);
        },
        add: function(m) {
            var action_view = new ActionView({
                model: m
            });
            var pos = this.collection.models.indexOf(m);

            // Always adding to the end is wrong
            this._my_element_views.splice(pos, 0, action_view);
            this.render(); 
        },
        remove: function(view, collection, options) {
            this._my_element_views.splice(options.index, 1);
            //$.each(this._my_element_views, function (key, action_view) {
                //console.log('remaining views:');
                //console.log(action_view.model.attributes.name);
                //console.log(action_view.state);
            //});
        },
        render: function() {
            var ell = this.$el;
            ell.children().remove()
            $.each(this._my_element_views, function (key, action_view) {
                    ell.append(action_view.render().el);
                });

            this.delegateEvents();
            return this;
        },    
        update_sort: function(event, model, position) {            
            var that=this;
            //var log_order = function() {
                //$.each(that.collection.models, function (key, m) {
                    //console.log(m.attributes.id + ' ' + m.attributes.name);
                //});
            //}
            this.collection.remove(model);

            this.collection.each(function (m, index) {
                if (index >= position)
                    index += 1;
                m.set('index', index);
            });            
            
            model.set('index', position);
            this.collection.add(model, {at: position});
            
            // to update ordinals on server:
            var ids = this.collection.pluck('id');

            $.ajax(window.location + "/action-order", {
                data : JSON.stringify({'order': ids}),
                contentType : 'application/json',
                type : 'POST'});
            
            this.render();
        }
    });

    var action_set = new ActionSet();
    action_set.add(action_data);

    var action_set_view = new ActionSetView({
        el: $('#deployment-actions'),
        collection: action_set,
    });
    action_set_view.render();

    window.ActionApp = action_set;
});
