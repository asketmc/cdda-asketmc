#pragma once

namespace audio_retry_policy
{

template<typename Attempt, typename Delay>
bool try_twice( Attempt &&attempt, Delay &&delay )
{
    if( attempt( 1 ) ) {
        return true;
    }
    delay();
    return attempt( 2 );
}

template<typename Initialize, typename Restore, typename Quit>
bool initialize_temporary_backend( Initialize &&initialize, Restore &&restore, Quit &&quit )
{
    const bool initialized = initialize();
    if( !restore() ) {
        if( initialized ) {
            quit();
        }
        return false;
    }
    return initialized;
}

} // namespace audio_retry_policy
