void _fix_range(inout float value, inout float range)
{
    if(range < 0)
    {
        range = abs(range);
        value -= range;
    }
}

float line_width_2(
    sampler2D normal_depth_texture, usampler2D id_texture,
    float width_scale, int width_units,
    float depth_width, float depth_threshold, float depth_threshold_range,
    float normal_width, float normal_threshold, float normal_threshold_range,
    vec4 id_boundary_width
)
{
    depth_threshold = pow(depth_threshold, 10) * 999 + 1;
    if (depth_threshold_range > 0)
        depth_threshold_range = pow(depth_threshold_range, 10) * 1000;

    LineDetectionOutput lo = line_detection_2(
        normal_depth_texture,
        3,
        normal_depth_texture,
        id_texture
    );

    float line = 0;

    vec4 id = vec4(lo.id_boundary) * id_boundary_width;
    
    for(int i = 0; i < 4; i++)
    {
        line = max(line, id[i]);
    }

    _fix_range(depth_threshold, depth_threshold_range);

    if(lo.delta_distance > depth_threshold)
    {
        float depth = depth_width;
        if(depth_threshold_range != 0)
        {
            depth = map_range_clamped(
                lo.delta_distance, 
                depth_threshold, depth_threshold + depth_threshold_range,
                0, depth_width
            );
        }

        line = max(line, depth);
    }

    _fix_range(normal_threshold, normal_threshold_range);

    normal_threshold = max(0.01, normal_threshold);

    if(lo.delta_angle > normal_threshold)
    {
        float angle = normal_width;
        if(normal_threshold_range != 0)
        {
            angle = map_range_clamped(
                lo.delta_angle, 
                normal_threshold, normal_threshold + normal_threshold_range,
                0, normal_width
            );
        }

        line = max(line, angle);
    }

    if(width_units == 1)//Screen %
    {
        width_scale *= length(vec2(RESOLUTION)) / 1000.0;
    }
    if(width_units == 2)//World
    {
        width_scale /= pixel_world_size() * 100.0;
    }
            
    return line * width_scale;
}