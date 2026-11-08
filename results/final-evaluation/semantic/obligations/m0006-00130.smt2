(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x5401 (bvule s_3 (_ bv7 4))))
(not $x5401)))
(check-sat)
