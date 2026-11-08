(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x994 (bvule s_7 (_ bv128 8))))
(not $x994)))
(check-sat)
