(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x1134 (and (distinct s_7 (_ bv128 8)) true)))
(not $x1134)))
(check-sat)
