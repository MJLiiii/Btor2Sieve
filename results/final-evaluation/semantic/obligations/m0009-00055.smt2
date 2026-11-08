(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x3395 (and (distinct s_6 (_ bv15 4)) true)))
(not $x3395)))
(check-sat)
