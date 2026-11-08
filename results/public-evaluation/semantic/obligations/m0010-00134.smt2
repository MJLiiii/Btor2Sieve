(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x150 (bvule i_7 (_ bv128 8))))
(not $x150)))
(check-sat)
