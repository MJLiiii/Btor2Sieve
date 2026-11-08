(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x1303 (and (distinct s_7 (_ bv0 8)) true)))
(not $x1303)))
(check-sat)
