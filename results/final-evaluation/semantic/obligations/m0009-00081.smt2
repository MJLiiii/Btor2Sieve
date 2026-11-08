(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x6734 (and (distinct s_7 (_ bv128 8)) true)))
(not $x6734)))
(check-sat)
