#include "Common.glsl"
#include "Filters/Line.glsl"
#include "LineFilter.glsl"

#ifdef VERTEX_SHADER
void main() {
    #ifdef PRE_PASS
    DEFAULT_VERTEX_SHADER();
    #endif //PRE_PASS
    #ifdef MAIN_PASS
    DEFAULT_VERTEX_SHADER();
    #endif //MAIN_PASS
    #ifdef LINE_PASS
    DEFAULT_SCREEN_VERTEX_SHADER();
    #endif //LINE_PASS
}
#endif

#ifdef PIXEL_SHADER
#ifdef PRE_PASS
layout(location = 0) out vec4 OUT_NORMAL_DEPTH;
layout(location = 1) out uvec4 OUT_ID;
#endif //PRE_PASS

#ifdef MAIN_PASS
uniform sampler2D IN_NORMAL_DEPTH;
uniform usampler2D IN_ID;

layout(location = 0) out vec4 OUT_LINECOLOR;
layout(location = 1) out float OUT_LINEWIDTH;
#endif //MAIN_PASS

#ifdef LINE_PASS
uniform sampler2D IN_NORMAL_DEPTH;
uniform usampler2D IN_ID;
uniform sampler2D IN_LINE_COLOR;
uniform sampler2D IN_LINE_WIDTH;

layout(location = 0) out vec4 OUT_LINE;
#endif //LINE_PASS

void main() {
    PIXEL_SETUP_INPUT();

    #ifdef PRE_PASS
    OUT_NORMAL_DEPTH.xyz = NORMAL;
    OUT_NORMAL_DEPTH.w = gl_FragCoord.z;
    OUT_ID = ID;
    #endif //PRE_PASS

    #ifdef MAIN_PASS
    NORMAL = texelFetch(IN_NORMAL_DEPTH, ivec2(gl_FragCoord.xy), 0).xyz;
    ID = texelFetch(IN_ID, ivec2(gl_FragCoord.xy), 0);

    OUT_LINECOLOR = vec4(1, 1, 0, 1);
    OUT_LINEWIDTH = line_width_2(IN_NORMAL_DEPTH, IN_ID, 
                                2.0, 0, 
                                1.0, 0.5, 0.0, 
                                1.0, 0.5, 0.0, 
                                vec4(1,1,1,1));
    #endif //MAIN_PASS

    #ifdef LINE_PASS
    vec2 uv = UV[0];
    OUT_LINE = line_expand(uv, 10, IN_LINE_COLOR, IN_LINE_WIDTH, 0, 1.0, IN_NORMAL_DEPTH, 3, IN_ID, 0).color;
    #endif //LINE_PASS
}
#endif
