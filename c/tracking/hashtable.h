#ifndef TRACKING_HASHTABLE_H
#define TRACKING_HASHTABLE_H

#include <stdint.h>
#include "types.h"

/* Verstable hash table: obj_id → CreationInfo */
#define NAME creation_map
#define KEY_TY uintptr_t
#define VAL_TY CreationInfo
#include "../vendor/verstable.h"

#endif /* TRACKING_HASHTABLE_H */
